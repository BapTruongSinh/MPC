"""One-step adaptive Kalman filter for live soil-moisture estimation.

Runtime equations, scalar H = 1:

    x_prior = arx_prediction if available else previous posterior
    P_prior = P_post + Q
    e_k = z_k - x_prior
    d_k = (1 - b) / (1 - b ** (k + 1))
    R_k = clip((1 - d_k) * R_prev + d_k * (e_k ** 2 - P_prior), R_min, R_max)
    K_k = P_prior / (P_prior + R_k)
    x_post = x_prior + K_k * e_k
    P_post = (1 - K_k) * P_prior

Missing or skipped measurements carry the prior forward and leave R unchanged.
``AdaptiveKalmanCycle.step()`` never raises; unexpected errors are returned as
``CycleResult(cycle_status="error")``.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from ..ingestion import ProcessedRecord
from ..prediction import PredictionAdapter, PredictionInput, PredictionResult

logger = logging.getLogger(__name__)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _safe_getattr(obj: object, name: str, default: object) -> object:
    try:
        return getattr(obj, name, default)
    except Exception:  # noqa: BLE001
        return default


def _safe_finite_float_or_none(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return None
    return result if math.isfinite(result) else None


@dataclass(frozen=True)
class KalmanConfig:
    x0: float = 0.0
    P0: float = 1.0
    Q: float = 0.05
    R0: float = 1.0
    R_min: float = 0.05
    R_max: float = 15.0
    forgetting_factor_b: float = 0.95

    def __post_init__(self) -> None:
        for field_name, value in (
            ("x0", self.x0),
            ("P0", self.P0),
            ("Q", self.Q),
            ("R0", self.R0),
            ("R_min", self.R_min),
            ("R_max", self.R_max),
            ("forgetting_factor_b", self.forgetting_factor_b),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite, got {value!r}")
        if self.P0 <= 0.0:
            raise ValueError(f"P0 must be > 0, got {self.P0!r}")
        if self.Q < 0.0:
            raise ValueError(f"Q must be >= 0, got {self.Q!r}")
        if self.R0 <= 0.0:
            raise ValueError(f"R0 must be > 0, got {self.R0!r}")
        if not (0.0 < self.R_min < self.R_max):
            raise ValueError(
                f"Must satisfy 0 < R_min < R_max; "
                f"got R_min={self.R_min!r}, R_max={self.R_max!r}"
            )
        if not (self.R_min <= self.R0 <= self.R_max):
            raise ValueError(
                f"R0 must be in [R_min, R_max]; "
                f"got R0={self.R0!r}, R_min={self.R_min!r}, R_max={self.R_max!r}"
            )
        if not (0.0 < self.forgetting_factor_b < 1.0):
            raise ValueError(
                "forgetting_factor_b must be in (0, 1), "
                f"got {self.forgetting_factor_b!r}"
            )


@dataclass
class KalmanState:
    x_post: float
    P_post: float
    R: float
    step: int = 0

    @classmethod
    def from_config(cls, config: KalmanConfig) -> "KalmanState":
        return cls(x_post=config.x0, P_post=config.P0, R=config.R0)


@dataclass(frozen=True)
class CycleResult:
    timestamp: datetime
    cycle_index: int
    raw_soil_moisture: float | None
    preprocess_status: str
    arx_predicted: float | None
    x_prior: float
    P_prior: float
    innovation: float | None
    R: float
    K: float | None
    x_posterior: float
    P_posterior: float
    cycle_status: str
    adaptive_status: str
    latency_ms: float | None = None
    error_message: str | None = None


class AdaptiveKalmanCycle:
    def __init__(
        self,
        config: KalmanConfig,
        adapter: PredictionAdapter | None = None,
    ) -> None:
        self._config = config
        self._adapter = adapter
        self._state = KalmanState.from_config(config)
        self._history: list[ProcessedRecord] = []

    @property
    def state(self) -> KalmanState:
        return self._state

    @property
    def config(self) -> KalmanConfig:
        return self._config

    @property
    def history(self) -> list[ProcessedRecord]:
        return list(self._history)

    def step(
        self,
        record: ProcessedRecord,
        *,
        cycle_index: int,
    ) -> CycleResult:
        started_at = time.perf_counter()
        try:
            result = self._step_impl(record, cycle_index, started_at)
        except Exception as exc:  # noqa: BLE001
            logger.exception("KalmanCycle step %d raised unexpectedly", cycle_index)
            result = self._error_result(record, cycle_index, started_at, exc)

        self._append_history(record)
        self._state.step += 1
        return result

    def _step_impl(
        self,
        record: ProcessedRecord,
        cycle_index: int,
        started_at: float,
    ) -> CycleResult:
        state = self._state
        arx_predicted = self._adapter_prediction()
        x_prior = arx_predicted if arx_predicted is not None else state.x_post
        P_prior = state.P_post + self._config.Q

        z = record.soil_moisture
        preprocess_status = record.preprocess_status
        if z is None or preprocess_status == "skipped":
            return self._skip_measurement_result(
                record,
                cycle_index,
                started_at,
                arx_predicted,
                x_prior,
                P_prior,
            )

        innovation = z - x_prior
        adaptive_gain = _iae_adaptive_gain(
            self._config.forgetting_factor_b,
            state.step,
        )
        R_new = _clip(
            (1.0 - adaptive_gain) * state.R
            + adaptive_gain * (innovation * innovation - P_prior),
            self._config.R_min,
            self._config.R_max,
        )
        K = P_prior / (P_prior + R_new)
        x_post = x_prior + K * innovation
        P_post = (1.0 - K) * P_prior

        state.x_post = x_post
        state.P_post = P_post
        state.R = R_new

        return CycleResult(
            timestamp=record.raw.timestamp,
            cycle_index=cycle_index,
            raw_soil_moisture=record.raw.soil_moisture,
            preprocess_status=preprocess_status,
            arx_predicted=arx_predicted,
            x_prior=x_prior,
            P_prior=P_prior,
            innovation=innovation,
            R=R_new,
            K=K,
            x_posterior=x_post,
            P_posterior=P_post,
            cycle_status="ok",
            adaptive_status="R_updated",
            latency_ms=_elapsed_ms(started_at),
        )

    def _adapter_prediction(self) -> float | None:
        if self._adapter is None:
            return None

        min_history = getattr(self._adapter, "min_history_len", 0)
        if len(self._history) < min_history:
            return None

        window = self._history[-min_history:] if min_history > 0 else []
        result: PredictionResult = self._adapter.predict(
            PredictionInput(history=window)
        )
        if result.status != "ok":
            return None
        return result.value

    def _skip_measurement_result(
        self,
        record: ProcessedRecord,
        cycle_index: int,
        started_at: float,
        arx_predicted: float | None,
        x_prior: float,
        P_prior: float,
    ) -> CycleResult:
        self._state.x_post = x_prior
        self._state.P_post = P_prior
        return CycleResult(
            timestamp=record.raw.timestamp,
            cycle_index=cycle_index,
            raw_soil_moisture=record.raw.soil_moisture,
            preprocess_status=record.preprocess_status,
            arx_predicted=arx_predicted,
            x_prior=x_prior,
            P_prior=P_prior,
            innovation=None,
            R=self._state.R,
            K=None,
            x_posterior=x_prior,
            P_posterior=P_prior,
            cycle_status="skipped_no_measurement",
            adaptive_status="R_skipped",
            latency_ms=_elapsed_ms(started_at),
        )

    def _error_result(
        self,
        record: object,
        cycle_index: int,
        started_at: float,
        exc: Exception,
    ) -> CycleResult:
        raw = _safe_getattr(record, "raw", None)
        timestamp_raw = _safe_getattr(raw, "timestamp", _EPOCH)
        timestamp = timestamp_raw if isinstance(timestamp_raw, datetime) else _EPOCH
        preprocess_status_raw = _safe_getattr(record, "preprocess_status", "invalid")
        preprocess_status = (
            preprocess_status_raw
            if isinstance(preprocess_status_raw, str)
            else "invalid"
        )

        return CycleResult(
            timestamp=timestamp,
            cycle_index=cycle_index,
            raw_soil_moisture=_safe_finite_float_or_none(
                _safe_getattr(raw, "soil_moisture", None)
            ),
            preprocess_status=preprocess_status,
            arx_predicted=None,
            x_prior=self._state.x_post,
            P_prior=self._state.P_post,
            innovation=None,
            R=self._state.R,
            K=None,
            x_posterior=self._state.x_post,
            P_posterior=self._state.P_post,
            cycle_status="error",
            adaptive_status="skipped",
            latency_ms=_elapsed_ms(started_at),
            error_message=str(exc),
        )

    def _append_history(self, record: ProcessedRecord) -> None:
        if record is None:
            return
        try:
            self._history.append(record)
        except Exception:  # noqa: BLE001
            pass


def _iae_adaptive_gain(forgetting_factor: float, step_index: int) -> float:
    if step_index < 0:
        raise ValueError("step_index must be >= 0")
    denominator = 1.0 - forgetting_factor ** (step_index + 1)
    if denominator <= 0.0:
        return 1.0
    return (1.0 - forgetting_factor) / denominator


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000.0


def _clip(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))
