from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Mapping

# thông số các loại đất
FAO56_SOIL_PRESETS: dict[str, dict[str, float]] = {
    "sand": {"theta_fc": 0.10, "theta_wp": 0.04},
    "light_loam": {"theta_fc": 0.15, "theta_wp": 0.06},
    "loam": {"theta_fc": 0.32, "theta_wp": 0.15},
    "clay_loam": {"theta_fc": 0.35, "theta_wp": 0.23},
}

_CONFIG_FLOAT_FIELDS = (
    "crop_kc",  # hệ số cây trồng Kc
    "theta_fc",  # độ ẩm thể tích sức chứa đồng ruộng
    "theta_wp",  # độ ẩm thể tích điểm héo
    "root_depth_m",  # độ sâu vùng rễ, đơn vị m
    "depletion_fraction_p",  # tỷ lệ nước dễ dùng trước khi cây stress
    "et0_hour_mm",  # bốc thoát hơi chuẩn ET0 theo giờ, đơn vị mm/h
    "pump_efficiency",  # hiệu suất nước bơm thật sự tới vùng rễ
    "pump_flow_lps",  # lưu lượng bơm, đơn vị lít/giây
    "irrigation_area_m2",  # diện tích vùng tưới, đơn vị m2
)


@dataclass(frozen=True)
class Fao56Config:
    crop_kc: float = 1.0
    soil_type: str = "loam"
    theta_fc: float = FAO56_SOIL_PRESETS["loam"]["theta_fc"]
    theta_wp: float = FAO56_SOIL_PRESETS["loam"]["theta_wp"]
    root_depth_m: float = 0.3
    depletion_fraction_p: float = 0.5
    et0_hour_mm: float = 0.6
    pump_efficiency: float = 0.8
    pump_flow_lps: float = 0.001
    irrigation_area_m2: float = 0.25

    def __post_init__(self) -> None:
        _require_known_soil(self.soil_type)
        for name in _CONFIG_FLOAT_FIELDS:
            _require_finite(name, getattr(self, name))

        if self.crop_kc < 0.0:
            raise ValueError("crop_kc must be >= 0")
        if not (0.0 <= self.theta_wp < self.theta_fc <= 0.8):
            raise ValueError("theta values must satisfy 0 <= theta_wp < theta_fc <= 0.8")
        if self.root_depth_m <= 0.0:
            raise ValueError("root_depth_m must be > 0")
        if not (0.0 < self.depletion_fraction_p < 1.0):
            raise ValueError("depletion_fraction_p must satisfy 0 < p < 1")
        if self.et0_hour_mm < 0.0:
            raise ValueError("et0_hour_mm must be >= 0")
        if not (0.0 < self.pump_efficiency <= 1.0):
            raise ValueError("pump_efficiency must satisfy 0 < eta <= 1")
        if self.pump_flow_lps <= 0.0:
            raise ValueError("pump_flow_lps must be > 0")
        if self.irrigation_area_m2 <= 0.0:
            raise ValueError("irrigation_area_m2 must be > 0")

    @classmethod
    def from_soil_preset(cls, soil_type: str, **overrides: float | str) -> "Fao56Config":
        return cls(soil_type=soil_type, **{**soil_preset(soil_type), **overrides})


@dataclass(frozen=True)
class Fao56State:
    sensor_percent: float
    theta: float
    taw_mm: float
    raw_mm: float
    depletion_mm: float
    water_stress_ks: float

# mốc đổi độ ẩm sang FAO
@dataclass(frozen=True)
class SensorCalibration:
    field_capacity_percent: float # dr = 0 = target_high
    raw_percent: float # dr = RAW = target_low
    wilting_point_percent: float # dr = TAW

# kq 1 bước mô phỏng
@dataclass(frozen=True)
class Fao56Step:
    depletion_raw_next_mm: float  # Dr bước tiếp theo
    depletion_next_mm: float  # Dr bước tiếp theo  ép về [0, TAW]
    water_stress_ks: float  # hệ số stress nước của cây trong bước hiện tại
    et0_step_mm: float  # ET0 quy đổi cho một bước thời gian, đơn vị mm
    etc_adjusted_mm: float  # ETc đã chỉnh theo Kc và stress nước, đơn vị mm
    irrigation_depth_mm: float  # lượng nước tưới quy đổi từ thời gian bơm, đơn vị mm

# lấy thông số đất 
def soil_preset(soil_type: str) -> dict[str, float]:
    _require_known_soil(soil_type)
    return dict(FAO56_SOIL_PRESETS[soil_type])


def fao56_config_from_mapping(payload: Mapping[str, object] | None) -> Fao56Config:
    if payload is None:
        return Fao56Config()
    if not isinstance(payload, Mapping):
        raise ValueError("fao56 must be an object")

    soil_type = payload.get("soil_type", "loam")
    if not isinstance(soil_type, str):
        raise ValueError("fao56.soil_type must be a string")

    overrides = {
        key: _required_float(payload[key], f"fao56.{key}")
        for key in _CONFIG_FLOAT_FIELDS
        if key in payload
    }
    return Fao56Config.from_soil_preset(soil_type, **overrides)

# đổi từ dr sang theta dổ ẩm thế tích đất
def theta_from_depletion_mm(depletion_mm: float, config: Fao56Config) -> float:
    _require_finite("depletion_mm", depletion_mm)
    return config.theta_fc - depletion_mm / (1000.0 * config.root_depth_m)

# chuyển độ ẩm thành chuẩn FAO
def sensor_calibration_from_target_band(
    *,
    target_low: float,
    target_high: float,
    config: Fao56Config,
) -> SensorCalibration:
    _require_finite("target_low", target_low)
    _require_finite("target_high", target_high)
    if not (0.0 <= target_low < target_high <= 100.0):
        raise ValueError("target_low/target_high must satisfy 0 <= low < high <= 100")

    sensor_wp = target_high - (target_high - target_low) / config.depletion_fraction_p
    if sensor_wp < 0.0:
        raise ValueError(
            "sensor calibration requires sensor_wp_percent >= 0; "
            "narrow target_low/target_high or increase depletion_fraction_p"
        )
    return SensorCalibration(
        field_capacity_percent=target_high,
        raw_percent=target_low,
        wilting_point_percent=sensor_wp,
    )

# chuyển % độ ẩm thành dr
def calibrated_depletion_from_sensor_percent(
    sensor_percent: float,
    config: Fao56Config,
    *,
    target_low: float,
    target_high: float,
) -> float:
    _require_sensor_percent(sensor_percent)
    calibration, taw, sensor_span = _target_band_terms(config, target_low, target_high)
    depletion = (calibration.field_capacity_percent - sensor_percent) / sensor_span * taw
    return clamp(depletion, 0.0, taw)

# đổi từ dr sang % độ ẩm
def calibrated_sensor_percent_from_depletion_mm(
    depletion_mm: float,
    config: Fao56Config,
    *,
    target_low: float,
    target_high: float,
) -> float:
    calibration, taw, sensor_span = _target_band_terms(config, target_low, target_high)
    depletion = clamp_checked(depletion_mm, 0.0, taw, "depletion_mm")
    return calibration.field_capacity_percent - depletion / taw * sensor_span

# tính TAW
def total_available_water_mm(config: Fao56Config) -> float:
    return 1000.0 * (config.theta_fc - config.theta_wp) * config.root_depth_m

# tính RAW
def readily_available_water_mm(config: Fao56Config, taw_mm: float | None = None) -> float:
    taw = total_available_water_mm(config) if taw_mm is None else taw_mm
    _require_positive("taw_mm", taw)
    return config.depletion_fraction_p * taw

# đổi từ theta sang dr 
def depletion_from_theta_mm(
    theta: float,
    config: Fao56Config,
    taw_mm: float | None = None,
) -> float:
    _require_finite("theta", theta)
    taw = _taw_or_config(config, taw_mm)
    depletion = 1000.0 * (config.theta_fc - theta) * config.root_depth_m
    return clamp(depletion, 0.0, taw)

# tính hệ số stress của cây / ks
def water_stress_coefficient(
    depletion_mm: float,
    config: Fao56Config,
    taw_mm: float | None = None,
    raw_mm: float | None = None,
) -> float:
    _require_finite("depletion_mm", depletion_mm)
    taw = _taw_or_config(config, taw_mm)
    raw = readily_available_water_mm(config, taw) if raw_mm is None else raw_mm
    _require_finite("raw_mm", raw)
    if raw < 0.0:
        raise ValueError("raw_mm must be >= 0")
    if depletion_mm <= raw:
        return 1.0
    return clamp((taw - depletion_mm) / ((1.0 - config.depletion_fraction_p) * taw), 0.0, 1.0)

# đổi et0 sang mm/s
def et0_step_mm(et0_hour_mm: float, step_seconds: int | float) -> float:
    _require_finite("et0_hour_mm", et0_hour_mm)
    _require_finite("step_seconds", step_seconds)
    if et0_hour_mm < 0.0:
        raise ValueError("et0_hour_mm must be >= 0")
    if float(step_seconds) < 0.0:
        raise ValueError("step_seconds must be >= 0")
    return et0_hour_mm * float(step_seconds) / 3600.0
# tính ETc
def adjusted_crop_et_mm(
    water_stress_ks: float,
    et0_step_mm_value: float,
    config: Fao56Config,
) -> float:
    _require_finite("water_stress_ks", water_stress_ks)
    _require_finite("et0_step_mm", et0_step_mm_value)
    if not (0.0 <= water_stress_ks <= 1.0):
        raise ValueError("water_stress_ks must satisfy 0 <= Ks <= 1")
    if et0_step_mm_value < 0.0:
        raise ValueError("et0_step_mm must be >= 0")
    return water_stress_ks * config.crop_kc * et0_step_mm_value

 # đổi thời gian bật bơm sang lượng nước tưới quy 
def irrigation_depth_mm(pump_seconds: float, config: Fao56Config) -> float:
    _require_finite("pump_seconds", pump_seconds)
    if pump_seconds < 0.0:
        raise ValueError("pump_seconds must be >= 0")
    return config.pump_efficiency * config.pump_flow_lps * pump_seconds / config.irrigation_area_m2

# cập nhật dr sau 1 bước thời gian
def advance_depletion_mm(
    depletion_mm: float,
    et0_hour_mm: float,
    pump_seconds: float,
    step_seconds: int | float,
    config: Fao56Config,
) -> Fao56Step:
    taw, raw = _water_terms(config)
    current_depletion = clamp_checked(depletion_mm, 0.0, taw, "depletion_mm")
    ks = water_stress_coefficient(current_depletion, config, taw, raw)
    step_et0 = et0_step_mm(et0_hour_mm, step_seconds)
    adjusted_et = adjusted_crop_et_mm(ks, step_et0, config)
    irrigation = irrigation_depth_mm(pump_seconds, config)
    depletion_raw_next = current_depletion + adjusted_et - irrigation
    return Fao56Step(
        depletion_raw_next_mm=depletion_raw_next,
        depletion_next_mm=clamp(depletion_raw_next, 0.0, taw),
        water_stress_ks=ks,
        et0_step_mm=step_et0,
        etc_adjusted_mm=adjusted_et,
        irrigation_depth_mm=irrigation,
    )

# đưa độ ẩm về FaoState cho mpc xài
def state_from_calibrated_sensor_percent(
    sensor_percent: float,
    config: Fao56Config,
    *,
    target_low: float,
    target_high: float,
) -> Fao56State:
    depletion = calibrated_depletion_from_sensor_percent(
        sensor_percent,
        config,
        target_low=target_low,
        target_high=target_high,
    )
    taw, raw = _water_terms(config)
    return Fao56State(
        sensor_percent=sensor_percent,
        theta=theta_from_depletion_mm(depletion, config),
        taw_mm=taw,
        raw_mm=raw,
        depletion_mm=depletion,
        water_stress_ks=water_stress_coefficient(depletion, config, taw, raw),
    )


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def clamp_checked(value: float, lower: float, upper: float, field_name: str) -> float:
    _require_finite(field_name, value)
    if value < lower or value > upper:
        raise ValueError(f"{field_name} must satisfy {lower} <= value <= {upper}")
    return value


def _water_terms(config: Fao56Config) -> tuple[float, float]:
    taw = total_available_water_mm(config)
    return taw, readily_available_water_mm(config, taw)


def _target_band_terms(
    config: Fao56Config,
    target_low: float,
    target_high: float,
) -> tuple[SensorCalibration, float, float]:
    calibration = sensor_calibration_from_target_band(
        target_low=target_low,
        target_high=target_high,
        config=config,
    )
    return (
        calibration,
        total_available_water_mm(config),
        calibration.field_capacity_percent - calibration.wilting_point_percent,
    )


def _taw_or_config(config: Fao56Config, taw_mm: float | None) -> float:
    taw = total_available_water_mm(config) if taw_mm is None else taw_mm
    _require_positive("taw_mm", taw)
    return taw


def _require_positive(name: str, value: float) -> None:
    _require_finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0")


def _require_sensor_percent(value: float) -> None:
    _require_finite("sensor_percent", value)
    if not (0.0 <= value <= 100.0):
        raise ValueError("sensor_percent must satisfy 0 <= S <= 100")


def _required_float(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    _require_finite(field_name, result)
    return result


def _require_known_soil(soil_type: str) -> None:
    if soil_type not in FAO56_SOIL_PRESETS:
        allowed = ", ".join(sorted(FAO56_SOIL_PRESETS))
        raise ValueError(f"soil_type must be one of: {allowed}")


def _require_finite(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
