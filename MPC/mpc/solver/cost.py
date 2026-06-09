"""FAO-56 water-balance cost functions for the scipy MPC solver."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from mpc.control.fao56 import (
    advance_depletion_mm,
    calibrated_sensor_percent_from_depletion_mm,
    et0_step_mm,
    state_from_calibrated_sensor_percent,
)
from mpc.core.config import ControllerConfig


@dataclass(frozen=True)
class TrajectoryCost:
    total: float
    band: float
    terminal: float
    water: float
    switching: float
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
    config: ControllerConfig,
) -> Fao56Trajectory:
    if not pump_seconds:
        raise ValueError("trajectory must not be empty")
    if not isfinite(previous_pump_seconds):
        raise ValueError("previous_pump_seconds must be finite")

    max_pump_seconds = config.pump.max_seconds
    if max_pump_seconds <= 0.0:
        raise ValueError("pump.max_seconds must be > 0")

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

        step = advance_depletion_mm(
            depletion_mm=current_dr,
            et0_hour_mm=config.fao56.et0_hour_mm,
            pump_seconds=pump,
            step_seconds=config.step_seconds,
            config=config.fao56,
        )
        forecast_sensor = calibrated_sensor_percent_from_depletion_mm(
            step.depletion_next_mm,
            config.fao56,
            target_low=config.target_band.low,
            target_high=config.target_band.high,
        )
        if not (
            isfinite(step.depletion_raw_next_mm)
            and isfinite(step.depletion_next_mm)
            and isfinite(forecast_sensor)
        ):
            raise ValueError("FAO prediction must be finite")

        stress_error = max(0.0, step.depletion_next_mm - raw)
        overwater_error = max(0.0, -step.depletion_raw_next_mm)
        pump_ratio = pump / max_pump_seconds
        switch_ratio = abs(pump - previous_pump) / max_pump_seconds

        stress_total += config.cost.band_violation * stress_error * stress_error
        overwater_total += config.cost.band_violation * overwater_error * overwater_error
        water_total += config.cost.water_use * pump_ratio * pump_ratio
        switching_total += config.cost.switching * switch_ratio * switch_ratio

        previous_pump = pump
        current_dr = step.depletion_next_mm
        predicted_soil.append(forecast_sensor)
        predicted_dr.append(step.depletion_next_mm)
        ks_values.append(step.water_stress_ks)
        etc_values.append(step.etc_adjusted_mm)
        irrigation_values.append(step.irrigation_depth_mm)
        raw_next_values.append(step.depletion_raw_next_mm)

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
