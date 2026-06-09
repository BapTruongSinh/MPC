"""Controller state contracts used by the MPC solver."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping


MAX_TRUSTED_KALMAN_R = 15.0


def _finite_or_none(value: float | int | None, field_name: str) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{field_name} must be finite")
    return numeric


def _required_finite(value: float | int | None, field_name: str) -> float:
    numeric = _finite_or_none(value, field_name)
    if numeric is None:
        raise ValueError(f"{field_name} is required")
    return numeric


def _optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an int or null")
    return value


@dataclass(frozen=True)
class ControllerState:
    """Latest controller state from Kalman/live payload."""

    timestamp: datetime
    kf_x_posterior: float | None = None
    kf_R: float | None = None
    raw_soil_moisture: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    light: float | None = None
    last_pump_seconds: float = 0.0
    run_id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime")
        _finite_or_none(self.kf_x_posterior, "kf_x_posterior")
        _finite_or_none(self.kf_R, "kf_R")
        _finite_or_none(self.raw_soil_moisture, "raw_soil_moisture")
        _finite_or_none(self.temperature, "temperature")
        _finite_or_none(self.humidity, "humidity")
        _finite_or_none(self.light, "light")
        _required_finite(self.last_pump_seconds, "last_pump_seconds")
        _optional_int(self.run_id, "run_id")

    @property
    def soil_moisture(self) -> float:
        """Prefer trusted Kalman posterior, then fallback to raw soil moisture."""
        posterior = _finite_or_none(self.kf_x_posterior, "kf_x_posterior")
        kalman_r = _finite_or_none(self.kf_R, "kf_R")
        raw = _finite_or_none(self.raw_soil_moisture, "raw_soil_moisture")
        if kalman_r is not None and kalman_r > MAX_TRUSTED_KALMAN_R:
            if raw is not None:
                return raw
            raise ValueError("state requires raw_soil_moisture when kf_R is above 15")
        if posterior is not None:
            return posterior
        if raw is not None:
            return raw
        raise ValueError("state requires kf_x_posterior or raw_soil_moisture")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ControllerState":
        raw_ts = payload.get("timestamp")
        if isinstance(raw_ts, datetime):
            timestamp = raw_ts
        elif isinstance(raw_ts, str):
            timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        else:
            raise ValueError("timestamp must be an ISO string or datetime")

        return cls(
            timestamp=timestamp,
            kf_x_posterior=_finite_or_none(
                payload.get("kf_x_posterior"),
                "kf_x_posterior",
            ),
            kf_R=_finite_or_none(payload.get("kf_R"), "kf_R"),
            raw_soil_moisture=_finite_or_none(
                payload.get("raw_soil_moisture"),
                "raw_soil_moisture",
            ),
            temperature=_finite_or_none(payload.get("temperature"), "temperature"),
            humidity=_finite_or_none(payload.get("humidity"), "humidity"),
            light=_finite_or_none(payload.get("light"), "light"),
            last_pump_seconds=_required_finite(
                payload.get("last_pump_seconds", 0.0),
                "last_pump_seconds",
            ),
            run_id=_optional_int(payload.get("run_id"), "run_id"),
        )

