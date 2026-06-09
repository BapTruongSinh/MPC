"""ARX artifact adapter used as the Kalman prior predictor."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from math import cos, floor, isfinite, log1p, pi, sin
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ..ingestion import ProcessedRecord
from .base import PredictionAdapter, PredictionInput, PredictionResult

logger = logging.getLogger(__name__)

_RAW_COLUMN_ATTRS = {
    "Soil_Moisture": "soil_moisture",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Light": "light",
    "Drip": "drip",
    "Mist": "mist",
    "Fan": "fan",
}
_DERIVED_COLUMNS = frozenset(
    {
        "Light_log",
        "Temp_x_Humidity",
        "Temp_x_Light",
        "Humidity_x_Light",
        "Air_Dryness",
        "Temp_x_Air_Dryness",
        "Hour_sin",
        "Hour_cos",
        "Day_sin",
        "Day_cos",
    }
)
_DEFAULT_INPUT_COLS = ("Temperature", "Humidity", "Light", "Drip", "Mist", "Fan")


@dataclass(frozen=True)
class ScaleStat:
    mean: float
    std: float

    def __post_init__(self) -> None:
        if not isfinite(self.mean):
            raise ValueError("scale mean must be finite")
        if not isfinite(self.std) or self.std <= 0.0:
            raise ValueError("scale std must be finite and > 0")

    def transform(self, value: float) -> float:
        _require_finite(value, "scale value")
        return (value - self.mean) / self.std

    def inverse(self, value: float) -> float:
        _require_finite(value, "scaled value")
        return value * self.std + self.mean


@dataclass(frozen=True)
class ARXArtifactConfig:
    na: int
    nb: int
    nk: int
    sampling_seconds: int
    include_intercept: bool = True
    input_cols: tuple[str, ...] = _DEFAULT_INPUT_COLS
    output_col: str = "Soil_Moisture"
    scale: dict[str, ScaleStat] | None = None
    clip_scaled: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.na < 1:
            raise ValueError("na must be >= 1")
        if self.nb < 1:
            raise ValueError("nb must be >= 1")
        if self.nk < 1:
            raise ValueError("nk must be >= 1")
        if self.sampling_seconds <= 0:
            raise ValueError("sampling_seconds must be > 0")
        if self.output_col != "Soil_Moisture":
            raise ValueError("Kalman ARX adapter only supports Soil_Moisture output")
        unknown = [
            col
            for col in self.input_cols
            if col not in _RAW_COLUMN_ATTRS and col not in _DERIVED_COLUMNS
        ]
        if unknown:
            raise ValueError(f"Unsupported ARX input column(s): {unknown}")
        if self.scale is not None:
            missing = [
                col
                for col in (self.output_col, *self.input_cols)
                if col not in self.scale
            ]
            if missing:
                raise ValueError(f"ARX scale missing column(s): {missing}")
        if self.clip_scaled is not None:
            low, high = self.clip_scaled
            if not (isfinite(low) and isfinite(high) and low < high):
                raise ValueError("clip_scaled must be finite [low, high]")

    @property
    def max_lag(self) -> int:
        return max(self.na, self.nb + self.nk - 1)

    @property
    def min_history_len(self) -> int:
        return self.max_lag

    def param_names(self) -> tuple[str, ...]:
        names = [f"a{lag}" for lag in range(1, self.na + 1)]
        for column in self.input_cols:
            names.extend(
                f"b_{column}_{lag}"
                for lag in range(self.nk, self.nk + self.nb)
            )
        if self.include_intercept:
            names.append("intercept")
        return tuple(names)


class ARXPredictionAdapter(PredictionAdapter):
    """Runtime-only ARX adapter. It loads a trained JSON artifact; it never trains."""

    _KIND = "arx"

    def __init__(self, artifact_config: ARXArtifactConfig) -> None:
        self._config = artifact_config
        self._theta: np.ndarray | None = None

    @property
    def model_kind(self) -> str:
        return self._KIND

    @property
    def is_trained(self) -> bool:
        return self._theta is not None

    @property
    def min_history_len(self) -> int:
        return self._config.min_history_len

    @property
    def artifact_config(self) -> ARXArtifactConfig:
        return self._config

    def predict(self, inp: PredictionInput) -> PredictionResult:
        history = inp.history or []
        if self._theta is None:
            return self._unavailable("ARX artifact is not loaded")
        if len(history) < self.min_history_len:
            return self._unavailable(
                f"History too short: {len(history)} < {self.min_history_len}"
            )

        try:
            window = history[-self.min_history_len :]
            missing = _missing_required_fields(window, self._config)
            if missing:
                return self._unavailable(f"None values in history: {missing}")
            row = _build_prediction_row(window, self._config)
            prediction = _inverse_prediction(float(row @ self._theta), self._config)
            return PredictionResult(
                value=prediction,
                status="ok",
                model_kind=self._KIND,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("ARX predict failed")
            return self._error(f"Prediction error: {exc}")

    @classmethod
    def load_artifact(cls, path: Path) -> "ARXPredictionAdapter":
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("ARX artifact root must be an object")

        if "spec" in data and "theta" in data:
            return cls._load_clean_5s_format(data)
        if data.get("model") == "ARX" and "model_config" in data:
            return cls._load_legacy_pipeline_format(data)
        raise ValueError(
            f"Unrecognised ARX artifact format in {path}: expected clean 5s "
            "artifact with spec/theta or legacy model_config/theta_hat"
        )

    @classmethod
    def _load_clean_5s_format(cls, data: dict[str, Any]) -> "ARXPredictionAdapter":
        spec = _mapping(data.get("spec"), "spec")
        config = ARXArtifactConfig(
            na=int(spec["na"]),
            nb=int(spec["nb"]),
            nk=int(spec["nk"]),
            include_intercept=True,
            input_cols=tuple(data.get("input_cols") or _DEFAULT_INPUT_COLS),
            output_col=str(data.get("target", "Soil_Moisture")),
            sampling_seconds=int(data.get("sampling_seconds", 5)),
            scale=_scale_stats(data.get("scale")),
            clip_scaled=_clip_scaled(data.get("clip_scaled")),
        )
        return _adapter_from_theta(cls, config, data.get("theta"), "theta")

    @classmethod
    def _load_legacy_pipeline_format(cls, data: dict[str, Any]) -> "ARXPredictionAdapter":
        top_config = _mapping(data.get("model_config"), "model_config")
        best = data.get("best_candidate")
        source = best if isinstance(best, dict) and "theta_hat" in best else data
        source_config = _mapping(source.get("model_config", top_config), "model_config")
        config = ARXArtifactConfig(
            na=int(source_config["na"]),
            nb=int(source_config["nb"]),
            nk=int(source_config["nk"]),
            include_intercept=bool(source_config.get("include_intercept", False)),
            input_cols=tuple(source_config.get("input_cols", _DEFAULT_INPUT_COLS)),
            output_col=str(source_config.get("output_col", "Soil_Moisture")),
            sampling_seconds=int(source_config.get("sampling_seconds", 300)),
        )
        return _adapter_from_theta(cls, config, source.get("theta_hat"), "theta_hat")

    def _unavailable(self, reason: str) -> PredictionResult:
        return PredictionResult(None, "unavailable", self._KIND, reason)

    def _error(self, reason: str) -> PredictionResult:
        return PredictionResult(None, "error", self._KIND, reason)


def _adapter_from_theta(
    adapter_cls: type[ARXPredictionAdapter],
    config: ARXArtifactConfig,
    raw_theta: object,
    field_name: str,
) -> ARXPredictionAdapter:
    if not isinstance(raw_theta, list):
        raise ValueError(f"ARX artifact missing {field_name}")
    theta = np.asarray(raw_theta, dtype=float)
    expected = len(config.param_names())
    if len(theta) != expected:
        raise ValueError(
            f"ARX {field_name} has {len(theta)} parameters but config expects {expected}"
        )
    if not np.all(np.isfinite(theta)):
        raise ValueError(f"ARX {field_name} values must be finite")
    adapter = adapter_cls(config)
    adapter._theta = theta  # noqa: SLF001
    return adapter


def _build_prediction_row(
    history: Sequence[ProcessedRecord],
    config: ARXArtifactConfig,
) -> np.ndarray:
    origin = _timestamp(history[0])
    row: list[float] = []
    for lag in range(1, config.na + 1):
        row.append(_scaled("Soil_Moisture", history[-lag], config, origin))
    for column in config.input_cols:
        for lag in range(config.nk, config.nk + config.nb):
            row.append(_scaled(column, history[-lag], config, origin))
    if config.include_intercept:
        row.append(1.0)
    return np.asarray(row, dtype=float)


def _scaled(
    column: str,
    record: ProcessedRecord,
    config: ARXArtifactConfig,
    origin: datetime,
) -> float:
    value = _feature_value(column, record, origin)
    if config.scale is None:
        return value
    return config.scale[column].transform(value)


def _feature_value(column: str, record: ProcessedRecord, origin: datetime) -> float:
    raw = {
        name: _record_value(record, attr)
        for name, attr in _RAW_COLUMN_ATTRS.items()
    }
    light_log = log1p(max(raw["Light"], 0.0))
    air_dryness = 100.0 - raw["Humidity"]
    timestamp = _timestamp(record)
    hour = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0
    day_num = floor((timestamp - origin).total_seconds() / 86400.0)

    derived = {
        "Light_log": light_log,
        "Temp_x_Humidity": raw["Temperature"] * raw["Humidity"],
        "Temp_x_Light": raw["Temperature"] * light_log,
        "Humidity_x_Light": raw["Humidity"] * light_log,
        "Air_Dryness": air_dryness,
        "Temp_x_Air_Dryness": max(raw["Temperature"] - 20.0, 0.0)
        * max(air_dryness, 0.0)
        / 100.0,
        "Hour_sin": sin(2.0 * pi * hour / 24.0),
        "Hour_cos": cos(2.0 * pi * hour / 24.0),
        "Day_sin": sin(2.0 * pi * day_num / 7.0),
        "Day_cos": cos(2.0 * pi * day_num / 7.0),
    }
    value = raw[column] if column in raw else derived[column]
    _require_finite(value, column)
    return value


def _record_value(record: ProcessedRecord, attr: str) -> float:
    value = getattr(record, attr)
    if value is None:
        raise ValueError(f"record.{attr} is required")
    return float(value)


def _timestamp(record: ProcessedRecord) -> datetime:
    timestamp = record.raw.timestamp
    if not isinstance(timestamp, datetime):
        raise ValueError("record timestamp must be datetime")
    return timestamp


def _inverse_prediction(value: float, config: ARXArtifactConfig) -> float:
    prediction = value
    if config.clip_scaled is not None:
        low, high = config.clip_scaled
        prediction = min(max(prediction, low), high)
    if config.scale is not None:
        prediction = config.scale["Soil_Moisture"].inverse(prediction)
    _require_finite(prediction, "prediction")
    return prediction


def _missing_required_fields(
    history: Sequence[ProcessedRecord],
    config: ARXArtifactConfig,
) -> list[str]:
    attrs = {_RAW_COLUMN_ATTRS["Soil_Moisture"]}
    for column in config.input_cols:
        attr = _RAW_COLUMN_ATTRS.get(column)
        if attr is not None:
            attrs.add(attr)
    return sorted(
        {
            attr
            for record in history
            for attr in attrs
            if getattr(record, attr, None) is None
        }
    )


def _scale_stats(raw: object) -> dict[str, ScaleStat]:
    data = _mapping(raw, "scale")
    stats: dict[str, ScaleStat] = {}
    for column, values in data.items():
        value_map = _mapping(values, f"scale.{column}")
        stats[str(column)] = ScaleStat(
            mean=float(value_map["mean"]),
            std=float(value_map["std"]),
        )
    return stats


def _clip_scaled(raw: object) -> tuple[float, float] | None:
    if raw is None:
        return None
    if not isinstance(raw, list | tuple) or len(raw) != 2:
        raise ValueError("clip_scaled must be [low, high]")
    return float(raw[0]), float(raw[1])


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"ARX artifact missing {field_name}")
    return value


def _require_finite(value: float, field_name: str) -> None:
    if not isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite")
