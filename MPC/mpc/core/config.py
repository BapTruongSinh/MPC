from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

from mpc.control.fao56 import (
    Fao56Config,
    fao56_config_from_mapping,
    sensor_calibration_from_target_band,
)


def _require_finite(name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")

# độ ẩm mặc định
@dataclass(frozen=True)
class TargetBand:
    low: float = 55.0
    high: float = 65.0

    def __post_init__(self) -> None:
        _require_finite("target_band.low", self.low)
        _require_finite("target_band.high", self.high)
        if not (0.0 <= self.low < self.high <= 100.0):
            raise ValueError(
                "target band must satisfy 0 <= low < high <= 100"
            )

# thời gian bơm mặc định
@dataclass(frozen=True)
class PumpLimits:
    min_seconds: float = 0.0
    max_seconds: float = 300.0

    def __post_init__(self) -> None:
        for name, value in (
            ("pump.min_seconds", self.min_seconds),
            ("pump.max_seconds", self.max_seconds),
        ):
            _require_finite(name, value)
        if self.min_seconds < 0.0:
            raise ValueError("pump.min_seconds must be >= 0")
        if self.max_seconds <= self.min_seconds:
            raise ValueError("pump.max_seconds must be > pump.min_seconds")

    def clamp(self, pump_seconds: float) -> float:
        _require_finite("pump_seconds", pump_seconds)
        return min(max(pump_seconds, self.min_seconds), self.max_seconds)
# chí phí phạt mặc định
@dataclass(frozen=True)
class CostWeights:
    band_violation: float = 10.0 # phạt đất quá khô hay ẩm
    terminal_band_violation: float = 20.0 # phạt trạng thái cuối đk
    water_use: float = 0.2 # phạt lượng nước dùng
    switching: float = 0.5 # phạt bật tắt bơm

    def __post_init__(self) -> None:
        for name, value in (
            ("cost.band_violation", self.band_violation),
            ("cost.terminal_band_violation", self.terminal_band_violation),
            ("cost.water_use", self.water_use),
            ("cost.switching", self.switching),
        ):
            _require_finite(name, value)
            if value < 0.0:
                raise ValueError(f"{name} must be >= 0")


@dataclass(frozen=True)
class SafetyConfig:
    state_min: float = 0.0
    state_max: float = 100.0 # khoảng độ ẩm an toàn
    stale_after_seconds: int = 600 # thời gian tối đa cho phép không có dữ liệu mới
    fail_closed_pump_seconds: float = 0.0 # nếu có lỗi thì lệnh bơm = 0

    def __post_init__(self) -> None:
        _require_finite("safety.state_min", self.state_min)
        _require_finite("safety.state_max", self.state_max)
        _require_finite(
            "safety.fail_closed_pump_seconds",
            self.fail_closed_pump_seconds,
        )
        if self.state_min >= self.state_max:
            raise ValueError("safety.state_min must be < safety.state_max")
        if self.stale_after_seconds <= 0:
            raise ValueError("safety.stale_after_seconds must be > 0")
        if self.fail_closed_pump_seconds != 0.0:
            raise ValueError("fail-closed pump command must remain 0 seconds")

# gữi lệnh bơm xuống esp
@dataclass(frozen=True)
class ActuatorConfig:
    enabled: bool = False
    url: str | None = None
    bearer_token_env: str | None = None
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("actuator.enabled must be a boolean")
        if self.url is not None and not _non_empty_string(self.url):
            raise ValueError("actuator.url must be a non-empty string or null")
        if self.bearer_token_env is not None and not _non_empty_string(
            self.bearer_token_env,
        ):
            raise ValueError(
                "actuator.bearer_token_env must be a non-empty string or null"
            )
        _require_finite("actuator.timeout_seconds", self.timeout_seconds)
        if self.timeout_seconds <= 0.0:
            raise ValueError("actuator.timeout_seconds must be > 0")


@dataclass(frozen=True)
class ControllerConfig:
    step_seconds: int = 300
    horizon_steps: int = 12
    target_band: TargetBand = field(default_factory=TargetBand)
    pump: PumpLimits = field(default_factory=PumpLimits)
    cost: CostWeights = field(default_factory=CostWeights)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    fao56: Fao56Config = field(default_factory=Fao56Config)
    actuator: ActuatorConfig = field(default_factory=ActuatorConfig)

    def __post_init__(self) -> None:
        if self.step_seconds <= 0:
            raise ValueError("step_seconds must be > 0")
        if self.horizon_steps < 1:
            raise ValueError("horizon_steps must be >= 1")
        sensor_calibration_from_target_band(
            target_low=self.target_band.low,
            target_high=self.target_band.high,
            config=self.fao56,
        )


def controller_config_from_mapping(
    payload: Mapping[str, Any],
) -> ControllerConfig:
    target_raw = _mapping_or_empty(payload.get("target_band"), "target_band")
    pump_raw = _mapping_or_empty(payload.get("pump"), "pump")
    cost_raw = _mapping_or_empty(payload.get("cost"), "cost")
    safety_raw = _mapping_or_empty(payload.get("safety"), "safety")
    fao56_raw = _mapping_or_empty(payload.get("fao56"), "fao56")
    actuator_raw = _mapping_or_empty(payload.get("actuator"), "actuator")

    return ControllerConfig(
        step_seconds=_strict_int(
            payload.get("step_seconds", 300),
            "step_seconds",
        ),
        horizon_steps=_strict_int(
            payload.get("horizon_steps", 12),
            "horizon_steps",
        ),
        target_band=TargetBand(
            low=float(target_raw.get("low", 55.0)),
            high=float(target_raw.get("high", 65.0)),
        ),
        pump=PumpLimits(
            min_seconds=float(pump_raw.get("min_seconds", 0.0)),
            max_seconds=float(pump_raw.get("max_seconds", 300.0)),
        ),
        cost=CostWeights(
            band_violation=float(cost_raw.get("band_violation", 10.0)),
            terminal_band_violation=float(
                cost_raw.get("terminal_band_violation", 20.0)
            ),
            water_use=float(cost_raw.get("water_use", 0.2)),
            switching=float(cost_raw.get("switching", 0.5)),
        ),
        safety=SafetyConfig(
            state_min=float(safety_raw.get("state_min", 0.0)),
            state_max=float(safety_raw.get("state_max", 100.0)),
            stale_after_seconds=_strict_int(
                safety_raw.get("stale_after_seconds", 600),
                "safety.stale_after_seconds",
            ),
            fail_closed_pump_seconds=float(
                safety_raw.get("fail_closed_pump_seconds", 0.0)
            ),
        ),
        fao56=fao56_config_from_mapping(fao56_raw),
        actuator=ActuatorConfig(
            enabled=_strict_bool(
                actuator_raw.get("enabled", False),
                "actuator.enabled",
            ),
            url=_optional_string(actuator_raw.get("url"), "actuator.url"),
            bearer_token_env=_optional_string(
                actuator_raw.get("bearer_token_env"),
                "actuator.bearer_token_env",
            ),
            timeout_seconds=float(actuator_raw.get("timeout_seconds", 5.0)),
        ),
    )


DEFAULT_CONFIG_ENV = "MPC_CONFIG_PATH"


def load_controller_config(path: str | Path | None) -> ControllerConfig:
    config_source = path
    if config_source is None:
        config_source = os.environ.get(DEFAULT_CONFIG_ENV)
    if config_source is None:
        return ControllerConfig()
    config_path = Path(config_source)
    with config_path.open("r", encoding="utf-8-sig") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("config JSON root must be an object")
    return controller_config_from_mapping(payload)


def _mapping_or_empty(value: Any, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _strict_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _strict_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string or null")
    return value


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
