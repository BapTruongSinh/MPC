from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize

from mpc.core.config import ControllerConfig
from mpc.core.state import ControllerState
from mpc.core.types import Recommendation, SafetyStatus
from mpc.solver.cost import Fao56Trajectory, score_fao56_trajectory


class ScipyMpcSolver:
    _MAX_FUTURE_SKEW_SECONDS = 30.0

    def __init__(self, config: ControllerConfig | None = None) -> None:
        self.config = config or ControllerConfig()
# đề xuất lệnh bơm
    def recommend(
        self,
        *,
        state: ControllerState,
        now: datetime | None = None,
    ) -> Recommendation:
        try:
            self._validate_state(state, now=now)
        except ValueError as exc:
            reason = str(exc)
            if "stale" in reason:
                return self._fail_closed("stale_sample", "stale_sample")
            return self._fail_closed("pump_off_failsafe", reason)

        try:
            best = self._solve(state=state)
        except RuntimeError as exc:
            return self._fail_closed("solver_error", str(exc))
        except Exception as exc:  # noqa: BLE001
            return self._fail_closed("model_error", str(exc))
        return Recommendation(
            pump_seconds=self.config.pump.clamp(best.pump_seconds[0]),
            step_seconds=self.config.step_seconds,
            predicted_soil_moisture=best.predicted_soil_moisture,
            target_band=self._target_band_payload(),
            cost=best.cost.total,
            safety_status="safe",
            reason=best.reason(),
            fao56=best.audit(),
        )
# tìm chuỗi bơm tối ưu nhất
    def _solve(self, *, state: ControllerState) -> Fao56Trajectory:
        horizon = self.config.horizon_steps
        result = minimize(
            lambda values: self._objective(values, state=state),
            x0=np.asarray(_initial_pump_guess(self.config, state), dtype=float),
            bounds=[_pump_bounds(self.config) for _ in range(horizon)],
            method="Powell",
            options=_optimizer_options(horizon),
        )
        if not result.success or result.x is None:
            raise RuntimeError(f"scipy_optimizer_failed:{result.message}")

        return self._score_sequence(state=state, sequence=_snapped_sequence(result.x, self.config))

    def _objective(
        self,
        values: np.ndarray,
        *,
        state: ControllerState,
    ) -> float:
        try:
            sequence = tuple(self.config.pump.clamp(float(value)) for value in values)
            return self._score_sequence(state=state, sequence=sequence).cost.total
        except Exception:
            return float("inf")

    def _score_sequence(
        self,
        *,
        state: ControllerState,
        sequence: tuple[float, ...],
    ) -> Fao56Trajectory:
        return score_fao56_trajectory(
            initial_sensor_percent=state.soil_moisture,
            pump_seconds=sequence,
            previous_pump_seconds=state.last_pump_seconds,
            config=self.config,
        )

    def _validate_state(
        self,
        state: ControllerState,
        *,
        now: datetime | None,
    ) -> None:
        soil_moisture = state.soil_moisture
        if not (
            self.config.safety.state_min
            <= soil_moisture
            <= self.config.safety.state_max
        ):
            raise ValueError("state_out_of_bounds")

        current_time = _as_aware_utc(now or datetime.now(timezone.utc))
        sample_time = _as_aware_utc(state.timestamp)
        age_seconds = (current_time - sample_time).total_seconds()
        if age_seconds < -self._MAX_FUTURE_SKEW_SECONDS:
            raise ValueError("future_sample")
        if age_seconds > self.config.safety.stale_after_seconds:
            raise ValueError("stale_sample")

    def _fail_closed(
        self,
        safety_status: SafetyStatus,
        reason: str,
    ) -> Recommendation:
        return Recommendation(
            pump_seconds=self.config.safety.fail_closed_pump_seconds,
            step_seconds=self.config.step_seconds,
            predicted_soil_moisture=(),
            target_band=self._target_band_payload(),
            cost=0.0,
            safety_status=safety_status,
            reason=reason,
        )

    def _target_band_payload(self) -> dict[str, float]:
        return {
            "low": self.config.target_band.low,
            "high": self.config.target_band.high,
        }


def recommend(
    *,
    state: ControllerState,
    config: ControllerConfig | None = None,
    now: datetime | None = None,
) -> Recommendation:
    return ScipyMpcSolver(config).recommend(
        state=state,
        now=now,
    )

# tạo chuỗi cho scipy đoán
def _initial_pump_guess(
    config: ControllerConfig,
    state: ControllerState,
) -> tuple[float, ...]:
    base = config.pump.clamp(state.last_pump_seconds)
    guess = [base] * config.horizon_steps
    if state.soil_moisture < config.target_band.low:
        guess[0] = config.pump.max_seconds
    return tuple(guess)


def _pump_bounds(config: ControllerConfig) -> tuple[float, float]:
    return (config.pump.min_seconds, config.pump.max_seconds)


def _optimizer_options(horizon_steps: int) -> dict[str, float | bool]:
    return {
        "maxiter": max(100, horizon_steps * 40),
        "xtol": 1e-4,
        "ftol": 1e-6,
        "disp": False,
    }


def _snapped_sequence(values: np.ndarray, config: ControllerConfig) -> tuple[float, ...]:
    return tuple(
        _snap_pump_seconds(config.pump.clamp(float(value)), config)
        for value in values
    )


def _snap_pump_seconds(value: float, config: ControllerConfig) -> float:
    tolerance = 1e-2
    if abs(value - config.pump.min_seconds) <= tolerance:
        return config.pump.min_seconds
    if abs(value - config.pump.max_seconds) <= tolerance:
        return config.pump.max_seconds
    return value


def _as_aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
