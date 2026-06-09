"""Controller state contracts used by the MPC solver."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping


MAX_TRUSTED_KALMAN_R = 15.0
OPTIONAL_STATE_FIELDS = (
    "kf_x_posterior",
    "kf_R",
    "raw_soil_moisture",
    "temperature",
    "humidity",
    "light",
)


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

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime")
        for field_name in OPTIONAL_STATE_FIELDS:
            _finite_or_none(getattr(self, field_name), field_name)
        _required_finite(self.last_pump_seconds, "last_pump_seconds")

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
        return cls(
            timestamp=_parse_timestamp(payload.get("timestamp")),
            **{
                field_name: _finite_or_none(payload.get(field_name), field_name)
                for field_name in OPTIONAL_STATE_FIELDS
            },
            last_pump_seconds=_required_finite(
                payload.get("last_pump_seconds", 0.0),
                "last_pump_seconds",
            ),
        )


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("timestamp must be an ISO string or datetime")

