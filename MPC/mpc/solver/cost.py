"""FAO-56 water-balance cost functions for the scipy MPC solver."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from mpc.control.fao56 import (
    adjusted_crop_et_mm,
    calibrated_sensor_percent_from_depletion_mm,
    et0_step_mm,
    irrigation_depth_mm,
    sensor_calibration_from_target_band,
    state_from_calibrated_sensor_percent,
    water_stress_coefficient,
)
from mpc.core.config import ControllerConfig


@dataclass(frozen=True)
class TrajectoryCost:
    total: float
    band: float
    terminal: float
    water: float
    switching: float
    daily_cap: float
    overwater: float = 0.0


@dataclass(frozen=True)
class Fao56Trajectory:
    pump_seconds: tuple[float, ...]
    cost: TrajectoryCost
    initial_depletion_mm: float
    taw_mm: float
    raw_mm: float
    initial_water_stress_ks: float
    et0_step_mm: float
    predicted_soil_moisture: tuple[float, ...]
    predicted_depletion_mm: tuple[float, ...]
    water_stress_ks: tuple[float, ...]
    etc_adjusted_mm: tuple[float, ...]
    irrigation_depth_mm: tuple[float, ...]
    depletion_raw_next_mm: tuple[float, ...]
    sensor_calibration_mode: str

    def reason(self) -> str:
        if self.initial_depletion_mm > self.raw_mm:
            return "above_raw_stress"
        if any(value > self.raw_mm for value in self.predicted_depletion_mm):
            return "forecast_above_raw_stress"
        if self.initial_depletion_mm <= 0.0:
            return "field_capacity_or_wetter"
        return "within_raw"

    def audit(self) -> dict[str, object]:
        return {
            "initial_dr": self.initial_depletion_mm,
            "taw": self.taw_mm,
            "raw": self.raw_mm,
            "ks": self.initial_water_stress_ks,
            "et0_step": self.et0_step_mm,
            "etc_adj": self.etc_adjusted_mm[0],
            "irrigation_depth_mm": self.irrigation_depth_mm[0],
            "predicted_dr": list(self.predicted_depletion_mm),
            "sensor_calibration_mode": self.sensor_calibration_mode,
        }


def score_fao56_trajectory(
    *,
    initial_sensor_percent: float,
    pump_seconds: Sequence[float],
    previous_pump_seconds: float,
    used_today_pump_seconds: float,
    config: ControllerConfig,
) -> Fao56Trajectory:
    if not pump_seconds:
        raise ValueError("trajectory must not be empty")
    if not isfinite(previous_pump_seconds):
        raise ValueError("previous_pump_seconds must be finite")
    if not isfinite(used_today_pump_seconds):
        raise ValueError("used_today_pump_seconds must be finite")
    if used_today_pump_seconds < 0.0:
        raise ValueError("used_today_pump_seconds must be >= 0")

    max_pump_seconds = config.pump.max_seconds
    daily_cap_seconds = config.safety.soft_daily_pump_cap_seconds
    if max_pump_seconds <= 0.0:
        raise ValueError("pump.max_seconds must be > 0")
    if daily_cap_seconds <= 0.0:
        raise ValueError("soft daily cap must be > 0")

    sensor_calibration_from_target_band(
        target_low=config.target_band.low,
        target_high=config.target_band.high,
        config=config.fao56,
    )
    fao_state = state_from_calibrated_sensor_percent(
        initial_sensor_percent,
        config.fao56,
        target_low=config.target_band.low,
        target_high=config.target_band.high,
    )
    taw = fao_state.taw_mm
    raw = fao_state.raw_mm
    current_dr = fao_state.depletion_mm
    step_et0 = et0_step_mm(config.fao56.et0_hour_mm, config.step_seconds)

    stress_total = 0.0
    overwater_total = 0.0
    water_total = 0.0
    switching_total = 0.0
    planned_pump = 0.0
    previous_pump = previous_pump_seconds
    predicted_soil: list[float] = []
    predicted_dr: list[float] = []
    ks_values: list[float] = []
    etc_values: list[float] = []
    irrigation_values: list[float] = []
    raw_next_values: list[float] = []

    for pump in pump_seconds:
        if not isfinite(pump):
            raise ValueError("pump_seconds must be finite")
        if pump < 0.0:
            raise ValueError("pump_seconds must be >= 0")
        if current_dr < 0.0 or current_dr > taw:
            raise ValueError("Dr must satisfy 0 <= Dr <= TAW")

        ks = water_stress_coefficient(current_dr, config.fao56, taw, raw)
        etc_adjusted = adjusted_crop_et_mm(ks, step_et0, config.fao56)
        irrigation = irrigation_depth_mm(pump, config.fao56)
        depletion_raw_next = current_dr + etc_adjusted - irrigation
        depletion_next = min(max(depletion_raw_next, 0.0), taw)
        forecast_sensor = calibrated_sensor_percent_from_depletion_mm(
            depletion_next,
            config.fao56,
            target_low=config.target_band.low,
            target_high=config.target_band.high,
        )
        if not (
            isfinite(depletion_raw_next)
            and isfinite(depletion_next)
            and isfinite(forecast_sensor)
        ):
            raise ValueError("FAO prediction must be finite")

        stress_error = max(0.0, depletion_next - raw)
        overwater_error = max(0.0, -depletion_raw_next)
        pump_ratio = pump / max_pump_seconds
        switch_ratio = abs(pump - previous_pump) / max_pump_seconds

        stress_total += config.cost.band_violation * stress_error * stress_error
        overwater_total += config.cost.band_violation * overwater_error * overwater_error
        water_total += config.cost.water_use * pump_ratio * pump_ratio
        switching_total += config.cost.switching * switch_ratio * switch_ratio

        planned_pump += pump
        previous_pump = pump
        current_dr = depletion_next
        predicted_soil.append(forecast_sensor)
        predicted_dr.append(depletion_next)
        ks_values.append(ks)
        etc_values.append(etc_adjusted)
        irrigation_values.append(irrigation)
        raw_next_values.append(depletion_raw_next)

    daily_excess_ratio = max(
        0.0,
        used_today_pump_seconds + planned_pump - daily_cap_seconds,
    ) / daily_cap_seconds
    daily_cap_total = (
        config.cost.daily_cap_excess
        * daily_excess_ratio
        * daily_excess_ratio
    )
    terminal_error = max(0.0, predicted_dr[-1] - raw)
    terminal_total = (
        config.cost.terminal_band_violation
        * terminal_error
        * terminal_error
    )
    total = (
        stress_total
        + overwater_total
        + water_total
        + switching_total
        + daily_cap_total
        + terminal_total
    )
    return Fao56Trajectory(
        pump_seconds=tuple(float(pump) for pump in pump_seconds),
        cost=TrajectoryCost(
            total=total,
            band=stress_total,
            terminal=terminal_total,
            water=water_total,
            switching=switching_total,
            daily_cap=daily_cap_total,
            overwater=overwater_total,
        ),
        initial_depletion_mm=fao_state.depletion_mm,
        taw_mm=taw,
        raw_mm=raw,
        initial_water_stress_ks=fao_state.water_stress_ks,
        et0_step_mm=step_et0,
        predicted_soil_moisture=tuple(predicted_soil),
        predicted_depletion_mm=tuple(predicted_dr),
        water_stress_ks=tuple(ks_values),
        etc_adjusted_mm=tuple(etc_values),
        irrigation_depth_mm=tuple(irrigation_values),
        depletion_raw_next_mm=tuple(raw_next_values),
        sensor_calibration_mode="target_band_to_raw",
    )
