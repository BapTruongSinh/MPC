from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from kalman.filter import AdaptiveKalmanCycle, KalmanConfig, KalmanState
from kalman.ingestion import ProcessedRecord, RawRecord, ValidationResult, preprocess_single, validate_live_record
from kalman.prediction import ARXPredictionAdapter

from .models import DeviceState, EstimationCycle, SensorData

HISTORY_LIMIT = 12
SENSOR_FIELDS = ('soil_moisture', 'temperature', 'humidity', 'light')
DEVICE_FLAGS = (('drip', 'pump', 'pump_on'), ('mist', 'mist', 'mist_on'), ('fan', 'fan', 'fan_on'))


def _number(value) -> float | None:
    return None if value is None else float(value)


def _device_flag(device_code: str) -> float:
    state = DeviceState.objects.filter(device_code=device_code).first()
    return float(bool(state and state.is_on))

# hàm đọc dữ liệu từ bảng sensor thành raw record
def _raw_from_reading(reading: SensorData) -> RawRecord:
    payload = reading.payload if isinstance(reading.payload, dict) else {}

    def flag(field: str, device: str) -> float:
        if field in payload:
            return _number(payload[field])
        if device in payload:
            return _number(payload[device])
        return _device_flag(device)

    return RawRecord(
        timestamp=reading.recorded_at,
        soil_moisture=_number(reading.soil_moisture),
        temperature=_number(reading.temperature),
        humidity=_number(reading.humidity),
        light=_number(reading.light),
        drip=flag('drip', 'pump'),
        mist=flag('mist', 'mist'),
        fan=flag('fan', 'fan'),
        row_index=0,
    )


@lru_cache(maxsize=4)
def _load_arx(path: str) -> ARXPredictionAdapter:
    return ARXPredictionAdapter.load_artifact(Path(path))

# lấy ARX model 
def _arx_adapter() -> ARXPredictionAdapter | None:
    path = str(getattr(settings, 'ARX_MODEL_PATH', ''))
    if not path:
        return None
    try:
        return _load_arx(path)
    except Exception:
        return None

# đọc config kalman
def _kalman_config(initial_soil: float | None) -> KalmanConfig:
    return KalmanConfig(
        x0=initial_soil or 0.0,
        Q=float(getattr(settings, 'KALMAN_LIVE_Q', 12.0)),
        R0=float(getattr(settings, 'KALMAN_LIVE_R0', 1.0)),
        R_min=float(getattr(settings, 'KALMAN_LIVE_R_MIN', 0.25)),
        R_max=float(getattr(settings, 'KALMAN_LIVE_R_MAX', 4.0)),
        forgetting_factor_b=float(getattr(settings, 'KALMAN_LIVE_FORGETTING_FACTOR_B', 0.95)),
    )

# lấy dữ liệu thô
def _processed_cycle(cycle: EstimationCycle) -> ProcessedRecord:
    raw = RawRecord(
        timestamp=cycle.sample_ts,
        soil_moisture=cycle.raw_soil_moisture,
        temperature=cycle.raw_temperature,
        humidity=cycle.raw_humidity,
        light=cycle.raw_light,
        drip=cycle.raw_drip,
        mist=cycle.raw_mist,
        fan=cycle.raw_fan,
        row_index=cycle.cycle_index,
    )
    validation = ValidationResult(
        is_valid=cycle.preprocess_status == EstimationCycle.PreprocessStatus.VALID,
        status=cycle.validation_status or 'valid',
        reason=cycle.validation_reason or '',
    )
    return preprocess_single(raw, validation)

# lấy dữ liệu đúng với owner
def _cycle_query(owner, source_type: str):
    return EstimationCycle.objects.filter(owner=owner, source_type=source_type)


def _build_estimator(
    initial_soil: float | None,
    owner,
    source_type: str,
) -> tuple[AdaptiveKalmanCycle, int]:
    adapter = _arx_adapter() if source_type == 'live' else None
    estimator = AdaptiveKalmanCycle(_kalman_config(initial_soil), adapter=adapter)
    cycles = _cycle_query(owner, source_type)
    latest = cycles.order_by('-cycle_index', '-id').first()
    cycle_index = latest.cycle_index + 1 if latest else 0
# Lấy kết quả độ ẩm sau lọc của vòng trước 
    if latest and all(value is not None for value in (latest.kf_x_posterior, latest.kf_P_posterior, latest.kf_R)):
        config = estimator.config
        estimator._state = KalmanState( 
            x_post=float(latest.kf_x_posterior),
            P_post=float(latest.kf_P_posterior),
            R=max(config.R_min, min(config.R_max, float(latest.kf_R))),
            step=cycle_index,
        )
# lấy ra 96 mẫu cho arx
    history_limit = max(getattr(adapter, 'min_history_len', 0), HISTORY_LIMIT)
    history = (
        cycles
        .filter(preprocess_status=EstimationCycle.PreprocessStatus.VALID)
        .exclude(raw_soil_moisture__isnull=True)
        .exclude(raw_temperature__isnull=True)
        .exclude(raw_humidity__isnull=True)
        .exclude(raw_light__isnull=True)
        .order_by('-sample_ts', '-id')[:history_limit]
    )
    estimator._history = [_processed_cycle(cycle) for cycle in reversed(list(history))]  # noqa: SLF001
    return estimator, cycle_index


def _create_cycle(
    raw: RawRecord,
    owner,
    dedupe_key: str,
    source_type: str,
) -> EstimationCycle:
    estimator, cycle_index = _build_estimator(raw.soil_moisture, owner, source_type)
    raw = replace(raw, row_index=cycle_index)
    validation = validate_live_record(raw)
    result = estimator.step(preprocess_single(raw, validation), cycle_index=cycle_index)
    has_measurement = raw.soil_moisture is not None
    kalman = {
        'arx_predicted': result.arx_predicted,
        'kf_x_prior': result.x_prior,
        'kf_P_prior': result.P_prior,
        'kf_innovation': result.innovation,
        'kf_R': result.R,
        'kf_K': result.K,
        'kf_x_posterior': result.x_posterior,
        'kf_P_posterior': result.P_posterior,
    } if has_measurement else {}
    return EstimationCycle.objects.create(
        sample_ts=result.timestamp,
        cycle_index=result.cycle_index,
        owner=owner,
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
        latency_ms=result.latency_ms,
        error_message=result.error_message or '',
        ingest_dedupe_key=dedupe_key,
        **kalman,
    )

# copy db + tạo
def ensure_estimation_for_reading(reading: SensorData) -> EstimationCycle:
    owner = reading.owner
    if owner is None:
        raise ValueError('sensor reading must belong to an owner')
    dedupe_key = f'live|sensor:{owner.pk}|{reading.recorded_at.astimezone().isoformat()}'
    existing = _cycle_query(owner, 'live').filter(ingest_dedupe_key=dedupe_key).first()
    return existing or _create_cycle(_raw_from_reading(reading), owner, dedupe_key, 'live')

# gộp data
def ensure_recent_window_estimations(
    *,
    owner,
    step_seconds: int,
    horizon_steps: int,
    end_time: datetime,
) -> EstimationCycle | None:
    if step_seconds <= 0 or horizon_steps < 1:
        raise ValueError('step_seconds and horizon_steps must be positive')

    aligned_end = _aligned_end(end_time, step_seconds)
    latest = None
    for index in range(horizon_steps, 0, -1):
        window_end = aligned_end - timedelta(seconds=step_seconds * (index - 1))
        latest = ensure_estimation_for_sensor_window(
            owner=owner,
            window_start=window_end - timedelta(seconds=step_seconds),
            window_end=window_end,
            step_seconds=step_seconds,
        ) or latest
    return latest

# gộp data cho mpc
def ensure_estimation_for_sensor_window(
    *,
    owner,
    window_start: datetime,
    window_end: datetime,
    step_seconds: int,
) -> EstimationCycle | None:
    if window_end <= window_start:
        raise ValueError('window_end must be after window_start')
    dedupe_key = (
        f'window|sensor:{owner.pk}|{step_seconds}|'
        f'{window_start.astimezone().isoformat()}|{window_end.astimezone().isoformat()}'
    )
    existing = _cycle_query(owner, 'live_window').filter(ingest_dedupe_key=dedupe_key).first()
    if existing is not None:
        return existing

    readings = list(
        SensorData.objects
        .filter(owner=owner, recorded_at__gt=window_start, recorded_at__lte=window_end)
        .order_by('recorded_at', 'id')
    )
    if not readings:
        return None

    values = {field: _average(readings, field) for field in SENSOR_FIELDS}
    flags = {name: _average_flag(readings, direct, state) for name, direct, state in DEVICE_FLAGS}
    raw = RawRecord(timestamp=window_end, row_index=0, **values, **flags)
    return _create_cycle(raw, owner, dedupe_key, 'live_window')


def _aligned_end(value: datetime, step_seconds: int) -> datetime:
    timestamp = value.timestamp()
    return datetime.fromtimestamp(timestamp - timestamp % step_seconds, tz=value.tzinfo)


def _average(readings: list[SensorData], field: str) -> float | None:
    values = [float(value) for reading in readings if (value := getattr(reading, field)) is not None]
    return sum(values) / len(values) if values else None


def _average_flag(readings: list[SensorData], direct_key: str, state_key: str) -> float:
    values = []
    for reading in readings:
        payload = reading.payload if isinstance(reading.payload, dict) else {}
        if direct_key in payload:
            values.append(float(_truthy(payload[direct_key])))
        elif isinstance(payload.get('device_states'), dict) and state_key in payload['device_states']:
            values.append(float(_truthy(payload['device_states'][state_key])))
    return sum(values) / len(values) if values else 0.0


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'on', 'yes'}


def latest_estimation(*, owner=None) -> EstimationCycle | None:
    queryset = EstimationCycle.objects.exclude(kf_x_posterior__isnull=True)
    if owner is not None:
        queryset = queryset.filter(owner=owner)
    return queryset.order_by('-sample_ts', '-id').first()
