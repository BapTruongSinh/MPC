"""Deterministic scipy.optimize MPC recommendation solver."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite

import numpy as np
from scipy.optimize import minimize

from mpc.core.config import ControllerConfig
from mpc.core.state import ControllerState
from mpc.core.types import Recommendation, SafetyStatus
from mpc.solver.cost import Fao56Trajectory, score_fao56_trajectory


class ScipyMpcSolver:
    """Optimize a future pump sequence and execute only the first command.

    Pump seconds are optimized as continuous decision variables with
    scipy.optimize, then the first command is executed by receding horizon.
    """

    _MAX_FUTURE_SKEW_SECONDS = 30.0

    def __init__(
        self,
        config: ControllerConfig | None = None,
    ) -> None:
        self.config = config or ControllerConfig()

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
            target_band={
                "low": self.config.target_band.low,
                "high": self.config.target_band.high,
            },
            cost=best.cost.total,
            safety_status="safe",
            reason=best.reason(),
            fao56=best.audit(),
        )

    def _solve(
        self,
        *,
        state: ControllerState,
    ) -> Fao56Trajectory:
        horizon = self.config.horizon_steps
        bounds = [
            (self.config.pump.min_seconds, self.config.pump.max_seconds)
            for _ in range(horizon)
        ]
        initial = _initial_pump_guess(self.config, state)

        result = minimize(
            lambda values: self._objective(
                values,
                state=state,
            ),
            x0=np.asarray(initial, dtype=float),
            bounds=bounds,
            method="Powell",
            options={
                "maxiter": max(100, horizon * 40),
                "xtol": 1e-4,
                "ftol": 1e-6,
                "disp": False,
            },
        )
        if not result.success or result.x is None:
            raise RuntimeError(f"scipy_optimizer_failed:{result.message}")

        sequence = tuple(
            _snap_pump_seconds(self.config.pump.clamp(float(value)), self.config)
            for value in result.x
        )
        return self._score_sequence(
            state=state,
            sequence=sequence,
        )

    def _objective(
        self,
        values: np.ndarray,
        *,
        state: ControllerState,
    ) -> float:
        try:
            sequence = tuple(
                self.config.pump.clamp(float(value))
                for value in values.tolist()
            )
            return self._score_sequence(
                state=state,
                sequence=sequence,
            ).cost.total
        except Exception:  # noqa: BLE001
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

        current_time = now or datetime.now(timezone.utc)
        sample_time = state.timestamp
        if sample_time.tzinfo is None:
            sample_time = sample_time.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
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
            target_band={
                "low": self.config.target_band.low,
                "high": self.config.target_band.high,
            },
            cost=0.0,
            safety_status=safety_status,
            reason=reason,
        )


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


def _initial_pump_guess(
    config: ControllerConfig,
    state: ControllerState,
) -> tuple[float, ...]:
    base = config.pump.clamp(state.last_pump_seconds)
    guess = [base] * config.horizon_steps
    if state.soil_moisture < config.target_band.low:
        guess[0] = config.pump.max_seconds
    return tuple(guess)


def _snap_pump_seconds(value: float, config: ControllerConfig) -> float:
    tolerance = 1e-2
    if abs(value - config.pump.min_seconds) <= tolerance:
        return config.pump.min_seconds
    if abs(value - config.pump.max_seconds) <= tolerance:
        return config.pump.max_seconds
    return value
