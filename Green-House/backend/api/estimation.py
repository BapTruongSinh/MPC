from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from datetime import datetime, timedelta

from django.conf import settings

from kalman.filter import AdaptiveKalmanCycle, KalmanConfig, KalmanState
from kalman.ingestion import (
    ProcessedRecord,
    RawRecord,
    ValidationResult,
    preprocess_single,
    validate_live_record,
)
from kalman.prediction import ARXPredictionAdapter

from .models import DeviceState, EstimationCycle, ExperimentRun, Greenhouse, SensorData


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _latest_device_flag(device_code: str) -> float:
    """Lấy trạng thái bật/tắt mới nhất từ DeviceState theo device_code."""
    state = DeviceState.objects.filter(device_code=device_code).first()
    return 1.0 if state and state.is_on else 0.0


def raw_record_from_reading(reading: SensorData, *, row_index: int) -> RawRecord:
    payload = reading.payload or {}
    return RawRecord(
        timestamp=reading.recorded_at,
        soil_moisture=_float_or_none(reading.soil_moisture),
        temperature=_float_or_none(reading.temperature),
        humidity=_float_or_none(reading.humidity),
        light=_float_or_none(reading.light),
        drip=_float_or_none(payload.get('drip')) if 'drip' in payload else _latest_device_flag('pump'),
        fan=_float_or_none(payload.get('fan')) if 'fan' in payload else _latest_device_flag('fan'),
        mist=_float_or_none(payload.get('mist')) if 'mist' in payload else _latest_device_flag('mist'),
        row_index=row_index,
    )


@lru_cache(maxsize=4)
def _load_arx_adapter(path: str) -> ARXPredictionAdapter:
    return ARXPredictionAdapter.load_artifact(Path(path))


def _prediction_adapter() -> ARXPredictionAdapter | None:
    path = str(getattr(settings, 'ARX_MODEL_PATH', ''))
    if not path:
        return None
    try:
        return _load_arx_adapter(path)
    except Exception:
        return None


def _live_kalman_config(initial_soil_moisture: float | None) -> KalmanConfig:
    return KalmanConfig(
        x0=_float_or_none(initial_soil_moisture) or 0.0,
        Q=float(getattr(settings, 'KALMAN_LIVE_Q', 12.0)),
        R0=float(getattr(settings, 'KALMAN_LIVE_R0', 1.0)),
        R_min=float(getattr(settings, 'KALMAN_LIVE_R_MIN', 0.25)),
        R_max=float(getattr(settings, 'KALMAN_LIVE_R_MAX', 4.0)),
        forgetting_factor_b=float(
            getattr(settings, 'KALMAN_LIVE_FORGETTING_FACTOR_B', 0.95)
        ),
    )


def _processed_from_cycle(cycle: EstimationCycle) -> ProcessedRecord:
    raw = RawRecord(
        timestamp=cycle.sample_ts,
        soil_moisture=cycle.raw_soil_moisture,
        temperature=cycle.raw_temperature,
        humidity=cycle.raw_humidity,
        light=cycle.raw_light,
        drip=cycle.raw_drip,
        fan=cycle.raw_fan,
        mist=cycle.raw_mist,
        row_index=cycle.cycle_index,
    )
    validation = ValidationResult(
        is_valid=cycle.preprocess_status == EstimationCycle.PreprocessStatus.VALID,
        status=cycle.validation_status or 'valid',
        reason=cycle.validation_reason or '',
    )
    return preprocess_single(raw, validation)


def _recent_processed_history(
    limit: int,
    *,
    run: ExperimentRun | None = None,
    greenhouse: Greenhouse | None = None,
) -> list[ProcessedRecord]:
    queryset = EstimationCycle.objects
    if run is not None:
        queryset = queryset.filter(run=run)
    elif greenhouse is not None:
        queryset = queryset.filter(greenhouse=greenhouse)
    cycles = (
        queryset
        .filter(preprocess_status=EstimationCycle.PreprocessStatus.VALID)
        .exclude(raw_soil_moisture__isnull=True)
        .exclude(raw_temperature__isnull=True)
        .exclude(raw_humidity__isnull=True)
        .exclude(raw_light__isnull=True)
        .order_by('-sample_ts', '-id')[:limit]
    )
    return [_processed_from_cycle(cycle) for cycle in reversed(list(cycles))]


def _restore_estimator_state(
    estimator: AdaptiveKalmanCycle,
    *,
    run: ExperimentRun | None = None,
    greenhouse: Greenhouse | None = None,
) -> int:
    queryset = EstimationCycle.objects
    if run is not None:
        queryset = queryset.filter(run=run)
    elif greenhouse is not None:
        queryset = queryset.filter(greenhouse=greenhouse)
    latest = queryset.order_by('-cycle_index', '-id').first()
    if latest is None:
        return 0

    if (
        latest.kf_x_posterior is not None
        and latest.kf_P_posterior is not None
        and latest.kf_R is not None
    ):
        config = estimator.config
        estimator._state = KalmanState(  # noqa: SLF001
            x_post=float(latest.kf_x_posterior),
            P_post=float(latest.kf_P_posterior),
            R=max(config.R_min, min(config.R_max, float(latest.kf_R))),
            step=latest.cycle_index + 1,
        )
    return latest.cycle_index + 1


def _create_estimation_cycle(
    *,
    raw: RawRecord,
    validation: ValidationResult,
    run: ExperimentRun | None,
    greenhouse: Greenhouse | None,
    ingest_dedupe_key: str,
    source_type: str,
) -> EstimationCycle:
    adapter = _prediction_adapter()
    estimator = AdaptiveKalmanCycle(_live_kalman_config(raw.soil_moisture), adapter=adapter)
    cycle_index = _restore_estimator_state(estimator, run=run, greenhouse=greenhouse)
    min_history = getattr(adapter, 'min_history_len', 0) if adapter is not None else 0
    estimator._history = _recent_processed_history(  # noqa: SLF001
        max(min_history, 12),
        run=run,
        greenhouse=greenhouse,
    )

    processed = preprocess_single(raw, validation)
    result = estimator.step(processed, cycle_index=cycle_index)
    has_soil_measurement = raw.soil_moisture is not None

    return EstimationCycle.objects.create(
        sample_ts=result.timestamp,
        cycle_index=result.cycle_index,
        run=run,
        greenhouse=greenhouse,
        slice_type='online',
        source_type=source_type,
        validation_status=validation.status,
        validation_reason=validation.reason,
        preprocess_status=result.preprocess_status,
        cycle_status=result.cycle_status,
        adaptive_status=result.adaptive_status,
        raw_soil_moisture=result.raw_soil_moisture,
        raw_temperature=raw.temperature,
        raw_humidity=raw.humidity,
        raw_light=raw.light,
        raw_drip=raw.drip,
        raw_mist=raw.mist,
        raw_fan=raw.fan,
        arx_predicted=result.arx_predicted if has_soil_measurement else None,
        kf_x_prior=result.x_prior if has_soil_measurement else None,
        kf_P_prior=result.P_prior if has_soil_measurement else None,
        kf_innovation=result.innovation if has_soil_measurement else None,
        kf_R=result.R if has_soil_measurement else None,
        kf_K=result.K if has_soil_measurement else None,
        kf_x_posterior=result.x_posterior if has_soil_measurement else None,
        kf_P_posterior=result.P_posterior if has_soil_measurement else None,
        latency_ms=result.latency_ms,
        error_message=result.error_message or '',
        ingest_dedupe_key=ingest_dedupe_key,
    )


def ensure_estimation_for_reading(
    reading: SensorData,
    *,
    run: ExperimentRun | None = None,
) -> EstimationCycle:
    greenhouse_key = reading.greenhouse_id or 'global'
    run_key = run.id if run is not None else f'sensor:{greenhouse_key}'
    ingest_dedupe_key = f"live|{run_key}|{reading.recorded_at.astimezone().isoformat()}"
    existing_query = EstimationCycle.objects.filter(ingest_dedupe_key=ingest_dedupe_key)
    if run is not None:
        existing_query = existing_query.filter(run=run)
    existing = existing_query.first()
    if existing is not None:
        return existing

    cycle_index = _restore_estimator_state(
        AdaptiveKalmanCycle(_live_kalman_config(_float_or_none(reading.soil_moisture))),
        run=run,
        greenhouse=reading.greenhouse,
    )
    raw = raw_record_from_reading(reading, row_index=cycle_index)
    validation = validate_live_record(raw)
    return _create_estimation_cycle(
        raw=raw,
        validation=validation,
        run=run,
        greenhouse=reading.greenhouse,
        ingest_dedupe_key=ingest_dedupe_key,
        source_type='live',
    )


def ensure_recent_window_estimations(
    *,
    greenhouse: Greenhouse,
    step_seconds: int,
    horizon_steps: int,
    end_time: datetime,
) -> EstimationCycle | None:
    """Create control-step estimation cycles from raw SensorData windows."""
    if step_seconds <= 0:
        raise ValueError('step_seconds must be > 0')
    if horizon_steps < 1:
        raise ValueError('horizon_steps must be >= 1')

    aligned_end = _aligned_window_end(end_time, step_seconds)
    latest: EstimationCycle | None = None
    for index in range(horizon_steps, 0, -1):
        window_end = aligned_end - timedelta(seconds=step_seconds * (index - 1))
        window_start = window_end - timedelta(seconds=step_seconds)
        cycle = ensure_estimation_for_sensor_window(
            greenhouse=greenhouse,
            window_start=window_start,
            window_end=window_end,
            step_seconds=step_seconds,
        )
        if cycle is not None:
            latest = cycle
    return latest


def ensure_estimation_for_sensor_window(
    *,
    greenhouse: Greenhouse,
    window_start: datetime,
    window_end: datetime,
    step_seconds: int,
) -> EstimationCycle | None:
    if window_end <= window_start:
        raise ValueError('window_end must be after window_start')
    dedupe_key = (
        f"window|sensor:{greenhouse.pk}|{step_seconds}|"
        f"{window_start.astimezone().isoformat()}|{window_end.astimezone().isoformat()}"
    )
    existing = EstimationCycle.objects.filter(
        greenhouse=greenhouse,
        ingest_dedupe_key=dedupe_key,
    ).first()
    if existing is not None:
        return existing

    readings = list(
        SensorData.objects
        .filter(
            greenhouse=greenhouse,
            recorded_at__gt=window_start,
            recorded_at__lte=window_end,
        )
        .order_by('recorded_at', 'id')
    )
    if not readings:
        return None

    cycle_index = _restore_estimator_state(
        AdaptiveKalmanCycle(_live_kalman_config(_average_field(readings, 'soil_moisture'))),
        greenhouse=greenhouse,
    )
    raw = RawRecord(
        timestamp=window_end,
        soil_moisture=_average_field(readings, 'soil_moisture'),
        temperature=_average_field(readings, 'temperature'),
        humidity=_average_field(readings, 'humidity'),
        light=_average_field(readings, 'light'),
        drip=_average_flag(readings, 'pump', 'pump_on'),
        mist=_average_flag(readings, 'mist', 'mist_on'),
        fan=_average_flag(readings, 'fan', 'fan_on'),
        row_index=cycle_index,
    )
    validation = validate_live_record(raw)
    return _create_estimation_cycle(
        raw=raw,
        validation=validation,
        run=None,
        greenhouse=greenhouse,
        ingest_dedupe_key=dedupe_key,
        source_type='live_window',
    )


def _aligned_window_end(value: datetime, step_seconds: int) -> datetime:
    timestamp = value.timestamp()
    aligned = timestamp - (timestamp % step_seconds)
    return datetime.fromtimestamp(aligned, tz=value.tzinfo)


def _average_field(readings: list[SensorData], field_name: str) -> float | None:
    values = [
        float(value)
        for reading in readings
        if (value := getattr(reading, field_name)) is not None
    ]
    return sum(values) / len(values) if values else None


def _average_flag(readings: list[SensorData], direct_key: str, state_key: str) -> float:
    values: list[float] = []
    for reading in readings:
        payload = reading.payload if isinstance(reading.payload, dict) else {}
        if direct_key in payload:
            values.append(1.0 if _truthy(payload[direct_key]) else 0.0)
            continue
        states = payload.get('device_states')
        if isinstance(states, dict) and state_key in states:
            values.append(1.0 if _truthy(states[state_key]) else 0.0)
    return sum(values) / len(values) if values else 0.0


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'on', 'yes'}


def latest_estimation(
    *,
    greenhouse: Greenhouse | None = None,
) -> EstimationCycle | None:
    queryset = EstimationCycle.objects
    if greenhouse is not None:
        queryset = queryset.filter(greenhouse=greenhouse)
    return (
        queryset
        .exclude(kf_x_posterior__isnull=True)
        .order_by('-sample_ts', '-id')
        .first()
    )
