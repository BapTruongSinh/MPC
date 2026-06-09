from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mpc.core.config import ControllerConfig, CostWeights, PumpLimits
from mpc.core.state import ControllerState
from mpc.solver import ScipyMpcSolver

NOW = datetime(2026, 5, 8, 10, 0, tzinfo=timezone.utc)


def _state(
    soil: float | None,
    *,
    last_pump_seconds: float = 0.0,
    timestamp: datetime = NOW,
) -> ControllerState:
    return ControllerState(
        timestamp=timestamp,
        kf_x_posterior=soil,
        raw_soil_moisture=None,
        temperature=27.0,
        humidity=72.0,
        light=300.0,
        last_pump_seconds=last_pump_seconds,
    )


def test_scipy_solver_in_band_prefers_no_pump() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(60.0),
        now=NOW,
    )

    assert recommendation.safety_status == "safe"
    assert recommendation.pump_seconds == 0.0
    assert recommendation.step_seconds == 300
    assert recommendation.reason == "within_raw"
    assert set(recommendation.to_dict()) == {
        "pump_seconds",
        "step_seconds",
        "predicted_soil_moisture",
        "target_band",
        "cost",
        "safety_status",
        "reason",
        "fao56",
    }
    assert recommendation.fao56 is not None
    assert recommendation.fao56["initial_dr"] == pytest.approx(12.75)
    assert recommendation.fao56["sensor_calibration_mode"] == "target_band_to_raw"


def test_scipy_solver_below_band_recommends_pump_from_water_balance() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(50.0),
        now=NOW,
    )

    assert recommendation.safety_status == "safe"
    assert 0.0 < recommendation.pump_seconds <= 300.0
    assert recommendation.reason == "above_raw_stress"
    assert recommendation.fao56 is not None
    assert recommendation.fao56["initial_dr"] > recommendation.fao56["raw"]
    assert recommendation.fao56["irrigation_depth_mm"] > 0.0
    assert recommendation.predicted_soil_moisture[0] > 50.0


def test_scipy_solver_uses_fao_rollout_without_history_dependency() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(50.0),
        now=NOW,
    )

    assert recommendation.safety_status == "safe"
    assert recommendation.fao56 is not None
    predicted_dr = recommendation.fao56["predicted_dr"]
    assert isinstance(predicted_dr, list)
    assert predicted_dr[0] < recommendation.fao56["initial_dr"]


def test_scipy_solver_above_band_recommends_no_pump() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(70.0),
        now=NOW,
    )

    assert recommendation.safety_status == "safe"
    assert recommendation.pump_seconds == 0.0
    assert recommendation.reason == "field_capacity_or_wetter"


def test_scipy_solver_respects_pump_bounds() -> None:
    config = ControllerConfig(pump=PumpLimits(max_seconds=60.0))

    recommendation = ScipyMpcSolver(config).recommend(
        state=_state(40.0),
        now=NOW,
    )

    assert 0.0 <= recommendation.pump_seconds <= 60.0


def test_scipy_solver_switching_penalty_can_preserve_previous_command() -> None:
    config = ControllerConfig(
        cost=CostWeights(
            band_violation=0.0,
            terminal_band_violation=0.0,
            water_use=0.0,
            switching=1.0,
        )
    )

    recommendation = ScipyMpcSolver(config).recommend(
        state=_state(60.0, last_pump_seconds=300.0),
        now=NOW,
    )

    assert recommendation.pump_seconds == pytest.approx(300.0)


def test_scipy_solver_returns_same_output_for_same_input() -> None:
    solver = ScipyMpcSolver()
    kwargs = {
        "state": _state(50.0),
        "now": NOW,
    }

    first = solver.recommend(**kwargs)
    second = solver.recommend(**kwargs)

    assert first == second


def test_scipy_solver_stale_state_fails_closed() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(60.0, timestamp=NOW - timedelta(seconds=601)),
        now=NOW,
    )

    assert recommendation.safety_status == "stale_sample"
    assert recommendation.pump_seconds == 0.0
    assert recommendation.predicted_soil_moisture == ()


def test_scipy_solver_future_timestamp_fails_closed() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(60.0, timestamp=NOW + timedelta(days=1)),
        now=NOW,
    )

    assert recommendation.safety_status == "pump_off_failsafe"
    assert recommendation.pump_seconds == 0.0


def test_scipy_solver_missing_state_fails_closed() -> None:
    recommendation = ScipyMpcSolver().recommend(
        state=_state(None),
        now=NOW,
    )

    assert recommendation.safety_status == "pump_off_failsafe"
    assert recommendation.pump_seconds == 0.0
