from __future__ import annotations

from datetime import datetime, time, timedelta

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from mpc.control.fao56 import Fao56Config
from mpc.core.config import (
    ControllerConfig,
    CostWeights,
    PumpLimits,
    SafetyConfig,
    TargetBand,
)
from mpc.core.state import MAX_TRUSTED_KALMAN_R, ControllerState
from mpc.core.types import Recommendation
from mpc.solver import ScipyMpcSolver

from .et0 import ET0Failure, ET0Reading, get_hourly_et0
from .estimation import (
    ensure_estimation_for_reading,
    ensure_recent_window_estimations,
    latest_estimation,
)
from .models import (
    AMPCRecommendation,
    ControlState,
    EstimationCycle,
    ExperimentRun,
    Greenhouse,
    GreenhouseControlProfile,
    SensorData,
)
from .services import enqueue_device_command, notify_pending_commands
from .user_resources import default_owner, ensure_user_greenhouse_config


def default_greenhouse(user=None) -> Greenhouse:
    owner = user if getattr(user, 'is_authenticated', False) else None
    if owner is None:
        owner = default_owner()

    greenhouse, _ = ensure_user_greenhouse_config(owner)
    return greenhouse


def get_greenhouse_control_profile(
    user=None,
    *,
    greenhouse: Greenhouse | None = None,
) -> GreenhouseControlProfile:
    """Return the control profile scoped to one greenhouse."""
    greenhouse = greenhouse or default_greenhouse(user)
    profile, _ = GreenhouseControlProfile.objects.get_or_create(
        greenhouse=greenhouse,
        defaults={'singleton_key': f'gh-{greenhouse.pk}'},
    )
    return profile


def profile_to_config(
    profile: GreenhouseControlProfile,
    *,
    et0_hour_mm: float | None = None,
) -> ControllerConfig:
    return ControllerConfig(
        step_seconds=profile.step_seconds,
        horizon_steps=profile.horizon_steps,
        target_band=TargetBand(low=profile.target_low, high=profile.target_high),
        pump=PumpLimits(
            min_seconds=profile.pump_min_seconds,
            max_seconds=profile.pump_max_seconds,
        ),
        cost=CostWeights(
            band_violation=profile.cost_band_violation,
            terminal_band_violation=profile.cost_terminal_band_violation,
            water_use=profile.cost_water_use,
            switching=profile.cost_switching,
            daily_cap_excess=profile.cost_daily_cap_excess,
        ),
        safety=SafetyConfig(
            stale_after_seconds=profile.safety_stale_after_seconds,
            soft_daily_pump_cap_seconds=profile.soft_daily_pump_cap_seconds,
        ),
        fao56=Fao56Config(
            crop_kc=profile.crop_kc,
            soil_type=getattr(profile, 'soil_type', 'loam'),
            theta_fc=getattr(profile, 'theta_fc', 0.32),
            theta_wp=getattr(profile, 'theta_wp', 0.15),
            root_depth_m=getattr(profile, 'root_depth_m', 0.30),
            depletion_fraction_p=getattr(profile, 'depletion_fraction_p', 0.5),
            et0_hour_mm=0.6 if et0_hour_mm is None else et0_hour_mm,
            pump_efficiency=getattr(profile, 'pump_efficiency', 0.8),
            pump_flow_lps=getattr(profile, 'pump_flow_lps', 0.001),
            irrigation_area_m2=getattr(profile, 'irrigation_area_m2', 0.25),
        ),
    )


def profile_snapshot(profile: GreenhouseControlProfile) -> dict:
    return {
        'crop_name': profile.crop_name,
        'crop_kc': profile.crop_kc,
        'latitude': getattr(profile, 'latitude', None),
        'longitude': getattr(profile, 'longitude', None),
        'soil_type': getattr(profile, 'soil_type', None),
        'theta_fc': getattr(profile, 'theta_fc', None),
        'theta_wp': getattr(profile, 'theta_wp', None),
        'root_depth_m': getattr(profile, 'root_depth_m', None),
        'depletion_fraction_p': getattr(profile, 'depletion_fraction_p', None),
        'pump_efficiency': getattr(profile, 'pump_efficiency', None),
        'pump_flow_lps': getattr(profile, 'pump_flow_lps', None),
        'irrigation_area_m2': getattr(profile, 'irrigation_area_m2', None),
        'target_low': profile.target_low,
        'target_high': profile.target_high,
        'step_seconds': profile.step_seconds,
        'horizon_steps': profile.horizon_steps,
        'pump_min_seconds': profile.pump_min_seconds,
        'pump_max_seconds': profile.pump_max_seconds,
        'soft_daily_pump_cap_seconds': profile.soft_daily_pump_cap_seconds,
        'weights': {
            'band': profile.cost_band_violation,
            'water': profile.cost_water_use,
            'switch': profile.cost_switching,
            'daily': profile.cost_daily_cap_excess,
            'terminal': profile.cost_terminal_band_violation,
        },
        'stale_after_seconds': profile.safety_stale_after_seconds,
        'actuator_enabled': profile.actuator_enabled,
    }


def _latest_control_state() -> ControlState:
    control, _ = ControlState.objects.get_or_create(singleton_key='main')
    return control


def _latest_pump_seconds(greenhouse: Greenhouse | None) -> float:
    queryset = AMPCRecommendation.objects
    if greenhouse is not None:
        queryset = queryset.filter(greenhouse=greenhouse)
    latest = queryset.order_by('-created_at', '-id').first()
    return float(latest.pump_seconds) if latest else 0.0


def _used_today_pump_seconds(
    now: datetime,
    *,
    greenhouse: Greenhouse | None,
) -> float:
    day = timezone.localtime(now).date()
    local_tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.combine(day, time.min), local_tz)
    day_end = day_start + timedelta(days=1)
    queryset = AMPCRecommendation.objects.filter(
        created_at__gte=day_start,
        created_at__lt=day_end,
        safety_status='safe',
        command_created=True,
    )
    if greenhouse is not None:
        queryset = queryset.filter(greenhouse=greenhouse)
    total = queryset.aggregate(total=Sum('pump_seconds')).get('total')
    return float(total or 0.0)


def _raw_fallback_delta() -> float:
    return float(getattr(settings, 'MPC_RAW_FALLBACK_DELTA', 8.0))


def _control_soil_moisture(cycle: EstimationCycle) -> float:
    raw = cycle.raw_soil_moisture
    posterior = cycle.kf_x_posterior
    kalman_r = cycle.kf_R
    if raw is not None and kalman_r is not None and float(kalman_r) > MAX_TRUSTED_KALMAN_R:
        return float(raw)
    if raw is not None and posterior is not None and abs(float(posterior) - float(raw)) > _raw_fallback_delta():
        return float(raw)
    if posterior is not None:
        return float(posterior)
    if raw is not None:
        return float(raw)
    raise ValueError('missing_soil_moisture')


def _uses_raw_fallback(cycle: EstimationCycle) -> bool:
    return (
        cycle.raw_soil_moisture is not None
        and (
            (
                cycle.kf_x_posterior is not None
                and abs(float(cycle.kf_x_posterior) - float(cycle.raw_soil_moisture)) > _raw_fallback_delta()
            )
            or (
                cycle.kf_R is not None
                and float(cycle.kf_R) > MAX_TRUSTED_KALMAN_R
            )
        )
    )


def _state_snapshot(
    estimation: EstimationCycle,
    state: ControllerState,
    *,
    recommendation: Recommendation | None = None,
    et0_result: ET0Reading | ET0Failure | None = None,
) -> dict:
    snapshot = {
        'estimation_id': estimation.id,
        'run_id': estimation.run_id,
        'timestamp': state.timestamp.isoformat(),
        'kf_x_posterior': estimation.kf_x_posterior,
        'kf_R': estimation.kf_R,
        'raw_soil_moisture': state.raw_soil_moisture,
        'control_soil_moisture': state.soil_moisture,
        'used_raw_fallback': _uses_raw_fallback(estimation),
        'temperature': state.temperature,
        'humidity': state.humidity,
        'light': state.light,
        'last_pump_seconds': state.last_pump_seconds,
    }
    if recommendation is not None and recommendation.fao56 is not None:
        snapshot['fao56'] = dict(recommendation.fao56)
        snapshot['fao56']['predicted_soil_moisture'] = list(recommendation.predicted_soil_moisture)
    if isinstance(et0_result, ET0Reading):
        snapshot['et0'] = {
            'requested_hour': et0_result.requested_hour.isoformat(),
            'et0_hour_mm': et0_result.et0_hour_mm,
            'et0_step_mm': et0_result.et0_step_mm,
            'step_seconds': et0_result.step_seconds,
            'source': et0_result.source,
            'fetched_at': et0_result.fetched_at.isoformat(),
        }
    elif isinstance(et0_result, ET0Failure):
        snapshot['et0'] = {
            'requested_hour': et0_result.requested_hour.isoformat(),
            'reason': et0_result.reason,
            'detail': et0_result.detail,
            'fail_closed': et0_result.fail_closed,
        }
    return snapshot


def _fail_recommendation(config: ControllerConfig, safety_status: str, reason: str) -> Recommendation:
    return Recommendation(
        pump_seconds=config.safety.fail_closed_pump_seconds,
        step_seconds=config.step_seconds,
        predicted_soil_moisture=(),
        target_band={'low': config.target_band.low, 'high': config.target_band.high},
        cost=0.0,
        safety_status=safety_status,
        reason=reason,
    )


def _bounded_ampc_recommendation_text(field_name: str, value) -> str:
    text = '' if value is None else str(value)
    max_length = AMPCRecommendation._meta.get_field(field_name).max_length
    if max_length is not None:
        return text[:max_length]
    return text


def _invalid_config_audit(
    *,
    profile: GreenhouseControlProfile,
    used_today: float,
    reason: str,
) -> AMPCRecommendation:
    config = ControllerConfig()
    recommendation = _fail_recommendation(config, 'config_error', reason)
    audit = _persist_recommendation(
        profile=profile,
        config=config,
        recommendation=recommendation,
        estimation=None,
        state=None,
        used_today=used_today,
        sensor_data=None,
        actuator_status=(
            AMPCRecommendation.ActuatorStatus.UNSAFE_SKIPPED
            if profile.actuator_enabled
            else AMPCRecommendation.ActuatorStatus.DISABLED
        ),
    )
    audit.state_snapshot = {
        'fail_closed': True,
        'config_error': reason,
    }
    audit.save(update_fields=['state_snapshot', 'updated_at'])
    return audit


def _persist_recommendation(
    *,
    profile: GreenhouseControlProfile,
    config: ControllerConfig,
    recommendation: Recommendation,
    estimation: EstimationCycle | None,
    state: ControllerState | None,
    used_today: float,
    run: ExperimentRun | None = None,
    sensor_data: SensorData | None = None,
    actuator_status: str = AMPCRecommendation.ActuatorStatus.NOT_CALLED,
    et0_result: ET0Reading | ET0Failure | None = None,
) -> AMPCRecommendation:
    control = _latest_control_state()
    safety_status = _bounded_ampc_recommendation_text('safety_status', recommendation.safety_status)
    reason = _bounded_ampc_recommendation_text('reason', recommendation.reason)
    return AMPCRecommendation.objects.create(
        sensor_data=sensor_data,
        greenhouse=profile.greenhouse,
        run=run,
        estimation=estimation,
        mode=control.mode,
        pump_seconds=float(recommendation.pump_seconds),
        step_seconds=int(recommendation.step_seconds),
        predicted_soil_moisture=list(recommendation.predicted_soil_moisture),
        target_band=dict(recommendation.target_band),
        objective_cost=float(recommendation.cost),
        safety_status=safety_status,
        reason=reason,
        used_today_pump_seconds=used_today,
        actuator_status=actuator_status,
        config_snapshot=profile_snapshot(profile),
        state_snapshot=(
            _state_snapshot(
                estimation,
                state,
                recommendation=recommendation,
                et0_result=et0_result,
            )
            if estimation and state
            else {}
        ),
    )


def _queue_pump_command(audit: AMPCRecommendation) -> AMPCRecommendation:
    if audit.safety_status != 'safe':
        audit.actuator_status = AMPCRecommendation.ActuatorStatus.UNSAFE_SKIPPED
        audit.save(update_fields=['actuator_status', 'updated_at'])
        return audit

    is_on = audit.pump_seconds > 0
    command = enqueue_device_command(
        device_code='pump',
        command='set_power',
        value='on' if is_on else 'off',
        payload={
            'source': 'mpc',
            'duration': round(audit.pump_seconds, 3) if is_on else 0,
            'recommendation_id': audit.id,
            'step_seconds': audit.step_seconds,
            'safety_status': audit.safety_status,
        },
    )
    audit.device_command = command
    audit.command_created = True
    audit.actuator_status = AMPCRecommendation.ActuatorStatus.QUEUED
    if is_on:
        audit.used_today_pump_seconds = float(audit.used_today_pump_seconds or 0.0) + float(audit.pump_seconds)
    audit.save(update_fields=[
        'device_command',
        'command_created',
        'actuator_status',
        'used_today_pump_seconds',
        'updated_at',
    ])
    notify_pending_commands()
    return audit


def run_auto_recommendation(
    *,
    create_command_if_auto: bool = True,
    user=None,
    greenhouse: Greenhouse | None = None,
) -> AMPCRecommendation:
    greenhouse = greenhouse or default_greenhouse(user)
    profile = get_greenhouse_control_profile(greenhouse=greenhouse)
    now = timezone.now()
    used_today = _used_today_pump_seconds(now, greenhouse=greenhouse)
    et0_result: ET0Reading | ET0Failure | None = None
    try:
        config = profile_to_config(profile)
    except ValueError as exc:
        return _invalid_config_audit(
            profile=profile,
            used_today=used_today,
            reason=f'invalid_fao_config:{exc}',
        )

    latest = ensure_recent_window_estimations(
        greenhouse=greenhouse,
        step_seconds=config.step_seconds,
        horizon_steps=config.horizon_steps,
        end_time=now,
    ) or latest_estimation(greenhouse=greenhouse)
    if latest is None:
        reading_query = SensorData.objects
        if greenhouse is not None:
            reading_query = reading_query.filter(greenhouse=greenhouse)
        reading = reading_query.order_by('-recorded_at', '-id').first()
        if reading is not None:
            latest = ensure_estimation_for_reading(reading)

    if latest is None:
        recommendation = _fail_recommendation(config, 'model_error', 'missing_estimation')
        return _persist_recommendation(
            profile=profile,
            config=config,
            recommendation=recommendation,
            estimation=None,
            state=None,
            used_today=used_today,
            sensor_data=None,
            actuator_status=(
                AMPCRecommendation.ActuatorStatus.UNSAFE_SKIPPED
                if profile.actuator_enabled
                else AMPCRecommendation.ActuatorStatus.DISABLED
            ),
        )

    sensor_query = SensorData.objects.filter(recorded_at=latest.sample_ts)
    if greenhouse is not None:
        sensor_query = sensor_query.filter(greenhouse=greenhouse)
    sensor_data = sensor_query.order_by('-id').first()
    use_raw_fallback = _uses_raw_fallback(latest)
    state = ControllerState(
        timestamp=latest.sample_ts,
        kf_x_posterior=None if use_raw_fallback else latest.kf_x_posterior,
        kf_R=latest.kf_R,
        raw_soil_moisture=latest.raw_soil_moisture,
        temperature=latest.raw_temperature,
        humidity=latest.raw_humidity,
        light=latest.raw_light,
        last_pump_seconds=_latest_pump_seconds(greenhouse),
        run_id=latest.run_id,
    )

    et0_result = get_hourly_et0(
        now,
        step_seconds=config.step_seconds,
        greenhouse=greenhouse,
    )
    if isinstance(et0_result, ET0Failure):
        recommendation = _fail_recommendation(
            config,
            'pump_off_failsafe',
            et0_result.reason,
        )
        audit = _persist_recommendation(
            profile=profile,
            config=config,
            recommendation=recommendation,
            estimation=latest,
            state=state,
            used_today=used_today,
            run=latest.run,
            sensor_data=sensor_data,
            actuator_status=(
                AMPCRecommendation.ActuatorStatus.DISABLED
                if not profile.actuator_enabled
                else AMPCRecommendation.ActuatorStatus.NOT_CALLED
            ),
            et0_result=et0_result,
        )
        control = _latest_control_state()
        if create_command_if_auto and profile.actuator_enabled and control.mode == ControlState.Mode.AUTO:
            return _queue_pump_command(audit)
        return audit

    try:
        config = profile_to_config(profile, et0_hour_mm=et0_result.et0_hour_mm)
    except ValueError as exc:
        return _invalid_config_audit(
            profile=profile,
            used_today=used_today,
            reason=f'invalid_fao_config:{exc}',
        )

    try:
        recommendation = ScipyMpcSolver(config).recommend(
            state=state,
            now=now,
            used_today_pump_seconds=used_today,
        )
    except Exception as exc:
        recommendation = _fail_recommendation(config, 'model_error', str(exc))

    audit = _persist_recommendation(
        profile=profile,
        config=config,
        recommendation=recommendation,
        estimation=latest,
        state=state,
        used_today=used_today,
        run=latest.run,
        sensor_data=sensor_data,
        actuator_status=AMPCRecommendation.ActuatorStatus.DISABLED if not profile.actuator_enabled else AMPCRecommendation.ActuatorStatus.NOT_CALLED,
        et0_result=et0_result,
    )

    control = _latest_control_state()
    if create_command_if_auto and profile.actuator_enabled and control.mode == ControlState.Mode.AUTO:
        return _queue_pump_command(audit)
    return audit


def latest_recommendation(
    *,
    greenhouse: Greenhouse | None = None,
) -> AMPCRecommendation | None:
    queryset = AMPCRecommendation.objects
    if greenhouse is not None:
        queryset = queryset.filter(greenhouse=greenhouse)
    return queryset.order_by('-created_at', '-id').first()
