"""Tests for one-step Adaptive Kalman runtime."""

from datetime import datetime, timezone

import pytest

from kalman.filter import AdaptiveKalmanCycle, KalmanConfig
from kalman.ingestion import ProcessedRecord, RawRecord, ValidationResult
from kalman.prediction import PredictionAdapter, PredictionInput, PredictionResult


def _record(sm: float | None, status: str = "valid") -> ProcessedRecord:
    raw = RawRecord(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        soil_moisture=sm,
        temperature=25.0,
        humidity=70.0,
        light=100.0,
        drip=0.0,
        fan=0.0,
        mist=0.0,
        row_index=0,
    )
    return ProcessedRecord(
        raw=raw,
        validation=ValidationResult(
            is_valid=sm is not None,
            status="valid" if sm is not None else "missing",
            reason="ok",
        ),
        preprocess_status=status,
        soil_moisture=sm,
        temperature=raw.temperature,
        humidity=raw.humidity,
        light=raw.light,
        drip=raw.drip,
        fan=raw.fan,
        mist=raw.mist,
    )


class FakeAdapter(PredictionAdapter):
    model_kind = "fake"
    is_trained = True
    min_history_len = 0

    def predict(self, inp: PredictionInput) -> PredictionResult:
        return PredictionResult(value=40.0, status="ok", model_kind="fake")

    @classmethod
    def load_artifact(cls, path):
        return cls()


def test_step_updates_state_with_measurement() -> None:
    est = AdaptiveKalmanCycle(KalmanConfig(x0=50.0, Q=0.05, R0=1.0))
    result = est.step(_record(52.0), cycle_index=0)
    assert result.cycle_status == "ok"
    assert result.adaptive_status == "R_updated"
    assert result.x_posterior != 50.0
    assert est.state.step == 1


def test_default_adaptive_r_cap_is_15() -> None:
    assert KalmanConfig().R_max == 15.0


def test_iae_r_update_subtracts_prior_covariance() -> None:
    config = KalmanConfig(
        x0=50.0,
        P0=1.0,
        Q=0.25,
        R0=4.0,
        R_min=0.05,
        R_max=100.0,
        forgetting_factor_b=0.5,
    )
    est = AdaptiveKalmanCycle(config)

    result = est.step(_record(53.0), cycle_index=0)

    innovation = 3.0
    p_prior = 1.25
    expected_r = innovation * innovation - p_prior
    assert result.R == pytest.approx(expected_r)
    assert result.K == pytest.approx(p_prior / (p_prior + expected_r))


def test_iae_uses_forgetting_factor_after_first_update() -> None:
    config = KalmanConfig(
        x0=50.0,
        P0=1.0,
        Q=0.0,
        R0=4.0,
        R_min=0.05,
        R_max=100.0,
        forgetting_factor_b=0.5,
    )
    est = AdaptiveKalmanCycle(config)
    first = est.step(_record(53.0), cycle_index=0)
    second = est.step(_record(55.0), cycle_index=1)

    adaptive_gain = (1.0 - config.forgetting_factor_b) / (
        1.0 - config.forgetting_factor_b**2
    )
    assert second.innovation is not None
    expected_r = (1.0 - adaptive_gain) * first.R + adaptive_gain * (
        second.innovation * second.innovation - second.P_prior
    )
    assert second.R == pytest.approx(expected_r)


def test_small_innovation_clips_iae_r_at_min() -> None:
    est = AdaptiveKalmanCycle(
        KalmanConfig(x0=50.0, P0=1.0, Q=0.05, R0=1.0, R_min=0.25)
    )
    result = est.step(_record(50.1), cycle_index=0)

    assert result.R == 0.25


def test_large_innovation_clips_r_at_15_by_default() -> None:
    est = AdaptiveKalmanCycle(KalmanConfig(x0=50.0), adapter=FakeAdapter())
    result = est.step(_record(80.0), cycle_index=0)

    assert result.R == 15.0


def test_step_skips_missing_measurement() -> None:
    config = KalmanConfig(x0=50.0, R0=2.5)
    est = AdaptiveKalmanCycle(config)
    result = est.step(_record(None, status="skipped"), cycle_index=0)
    assert result.cycle_status == "skipped_no_measurement"
    assert result.K is None
    assert result.R == config.R0


def test_adapter_prediction_becomes_prior() -> None:
    est = AdaptiveKalmanCycle(KalmanConfig(x0=50.0), adapter=FakeAdapter())
    result = est.step(_record(42.0), cycle_index=0)
    assert result.arx_predicted == 40.0
    assert result.x_prior == 40.0


def test_step_never_raises_on_bad_record() -> None:
    est = AdaptiveKalmanCycle(KalmanConfig())
    result = est.step(object(), cycle_index=3)  # type: ignore[arg-type]
    assert result.cycle_status == "error"
    assert result.error_message
