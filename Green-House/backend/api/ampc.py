from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.utils import timezone

from mpc.control.fao56 import Fao56Config
from mpc.core.config import ControllerConfig, CostWeights, PumpLimits, SafetyConfig, TargetBand
from mpc.core.state import MAX_TRUSTED_KALMAN_R, ControllerState
from mpc.core.types import Recommendation
from mpc.solver import ScipyMpcSolver

from .estimation import ensure_estimation_for_reading, ensure_recent_window_estimations, latest_estimation
from .et0 import ET0Reading, OpenMeteoError, get_hourly_et0
from .models import AMPCRecommendation, ControlState, EstimationCycle, GreenhouseControlProfile, SensorData
from .services import enqueue_device_command, notify_pending_commands
from .user_resources import control_owner, ensure_user_control_profile

PROFILE_SNAPSHOT_FIELDS = (
    'crop_name', 'crop_kc', 'latitude', 'longitude', 'soil_type', 'theta_fc',
    'theta_wp', 'root_depth_m', 'depletion_fraction_p', 'pump_efficiency',
    'pump_flow_lps', 'irrigation_area_m2', 'target_low', 'target_high',
    'step_seconds', 'horizon_steps', 'pump_min_seconds', 'pump_max_seconds',
    'safety_stale_after_seconds', 'actuator_enabled',
)


def default_control_owner(user=None):
    owner = control_owner(user)
    ensure_user_control_profile(owner)
    return owner


def get_control_profile(user=None, *, owner=None) -> GreenhouseControlProfile:
    return ensure_user_control_profile(owner or default_control_owner(user))


def profile_to_config(profile: GreenhouseControlProfile, *, et0_hour_mm: float = 0.6) -> ControllerConfig:
    return ControllerConfig(
        step_seconds=profile.step_seconds,
        horizon_steps=profile.horizon_steps,
        target_band=TargetBand(low=profile.target_low, high=profile.target_high),
        pump=PumpLimits(min_seconds=profile.pump_min_seconds, max_seconds=profile.pump_max_seconds),
        cost=CostWeights(
            band_violation=profile.cost_band_violation,
            terminal_band_violation=profile.cost_terminal_band_violation,
            water_use=profile.cost_water_use,
            switching=profile.cost_switching,
        ),
        safety=SafetyConfig(
            stale_after_seconds=profile.safety_stale_after_seconds,
        ),
        fao56=Fao56Config(
            crop_kc=profile.crop_kc,
            soil_type=profile.soil_type,
            theta_fc=profile.theta_fc,
            theta_wp=profile.theta_wp,
            root_depth_m=profile.root_depth_m,
            depletion_fraction_p=profile.depletion_fraction_p,
            et0_hour_mm=et0_hour_mm,
            pump_efficiency=profile.pump_efficiency,
            pump_flow_lps=profile.pump_flow_lps,
            irrigation_area_m2=profile.irrigation_area_m2,
        ),
    )


def profile_snapshot(profile: GreenhouseControlProfile) -> dict:
    snapshot = {field: getattr(profile, field) for field in PROFILE_SNAPSHOT_FIELDS}
    snapshot['weights'] = {
        'band': profile.cost_band_violation,
        'water': profile.cost_water_use,
        'switch': profile.cost_switching,
        'terminal': profile.cost_terminal_band_violation,
    }
    return snapshot


def latest_recommendation(*, owner=None) -> AMPCRecommendation | None:
    queryset = AMPCRecommendation.objects
    if owner is not None:
        queryset = queryset.filter(owner=owner)
    return queryset.order_by('-created_at', '-id').first()


def _uses_raw_fallback(cycle: EstimationCycle) -> bool:
    raw = cycle.raw_soil_moisture
    if raw is None:
        return False
    posterior_too_far = (
        cycle.kf_x_posterior is not None
        and abs(float(cycle.kf_x_posterior) - float(raw))
        > float(getattr(settings, 'MPC_RAW_FALLBACK_DELTA', 8.0))
    )
    uncertainty_too_high = cycle.kf_R is not None and float(cycle.kf_R) > MAX_TRUSTED_KALMAN_R
    return posterior_too_far or uncertainty_too_high


def _latest_estimation(owner, config: ControllerConfig, now: datetime) -> EstimationCycle | None:
    estimation = ensure_recent_window_estimations(
        owner=owner,
        step_seconds=config.step_seconds,
        horizon_steps=config.horizon_steps,
        end_time=now,
    ) or latest_estimation(owner=owner)
    if estimation is not None:
        return estimation
    reading = SensorData.objects.filter(owner=owner).order_by('-recorded_at', '-id').first()
    return ensure_estimation_for_reading(reading) if reading is not None else None


def _controller_state(estimation: EstimationCycle, owner) -> ControllerState:
    previous = latest_recommendation(owner=owner)
    return ControllerState(
        timestamp=estimation.sample_ts,
        kf_x_posterior=None if _uses_raw_fallback(estimation) else estimation.kf_x_posterior,
        kf_R=estimation.kf_R,
        raw_soil_moisture=estimation.raw_soil_moisture,
        temperature=estimation.raw_temperature,
        humidity=estimation.raw_humidity,
        light=estimation.raw_light,
        last_pump_seconds=float(previous.pump_seconds) if previous else 0.0,
    )


def _state_snapshot(
    estimation: EstimationCycle,
    state: ControllerState,
    recommendation: Recommendation,
    et0: ET0Reading | None,
) -> dict:
    snapshot = {
        'estimation_id': estimation.id,
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
    if recommendation.fao56 is not None:
        snapshot['fao56'] = {
            **recommendation.fao56,
            'predicted_soil_moisture': list(recommendation.predicted_soil_moisture),
        }
    if et0 is not None:
        snapshot['et0'] = {
            'requested_hour': et0.requested_hour.isoformat(),
            'et0_hour_mm': et0.et0_hour_mm,
            'et0_step_mm': et0.et0_step_mm,
            'step_seconds': et0.step_seconds,
        }
    return snapshot


def _failure(config: ControllerConfig, status: str, reason: str) -> Recommendation:
    return Recommendation(
        pump_seconds=config.safety.fail_closed_pump_seconds,
        step_seconds=config.step_seconds,
        predicted_soil_moisture=(),
        target_band={'low': config.target_band.low, 'high': config.target_band.high},
        cost=0.0,
        safety_status=status,
        reason=reason,
    )


def _bounded(field: str, value) -> str:
    length = AMPCRecommendation._meta.get_field(field).max_length
    return str(value or '')[:length] if length else str(value or '')


def _persist(
    profile: GreenhouseControlProfile,
    config: ControllerConfig,
    recommendation: Recommendation,
    *,
    estimation: EstimationCycle | None = None,
    state: ControllerState | None = None,
    et0: ET0Reading | None = None,
) -> AMPCRecommendation:
    sensor = None
    if estimation is not None:
        sensor = SensorData.objects.filter(
            owner=profile.owner,
            recorded_at=estimation.sample_ts,
        ).order_by('-id').first()
    control = ControlState.objects.get_or_create(singleton_key='main')[0]
    return AMPCRecommendation.objects.create(
        sensor_data=sensor,
        owner=profile.owner,
        estimation=estimation,
        mode=control.mode,
        pump_seconds=float(recommendation.pump_seconds),
        step_seconds=int(recommendation.step_seconds),
        predicted_soil_moisture=list(recommendation.predicted_soil_moisture),
        target_band=dict(recommendation.target_band),
        objective_cost=float(recommendation.cost),
        safety_status=_bounded('safety_status', recommendation.safety_status),
        reason=_bounded('reason', recommendation.reason),
        actuator_status=(
            AMPCRecommendation.ActuatorStatus.DISABLED
            if not profile.actuator_enabled
            else AMPCRecommendation.ActuatorStatus.NOT_CALLED
            if state is not None
            else AMPCRecommendation.ActuatorStatus.UNSAFE_SKIPPED
        ),
        config_snapshot=profile_snapshot(profile),
        state_snapshot=_state_snapshot(estimation, state, recommendation, et0) if estimation and state else {},
    )


def _persist_failure(
    profile: GreenhouseControlProfile,
    reason: str,
    *,
    config: ControllerConfig | None = None,
    status: str = 'model_error',
    estimation: EstimationCycle | None = None,
    state: ControllerState | None = None,
) -> AMPCRecommendation:
    config = config or ControllerConfig()
    audit = _persist(profile, config, _failure(config, status, reason), estimation=estimation, state=state)
    if status == 'config_error':
        audit.state_snapshot = {'fail_closed': True, 'config_error': reason}
        audit.save(update_fields=['state_snapshot', 'updated_at'])
    return audit


def _queue_pump_command(audit: AMPCRecommendation) -> AMPCRecommendation:
    if audit.safety_status != 'safe':
        audit.actuator_status = AMPCRecommendation.ActuatorStatus.UNSAFE_SKIPPED
        audit.save(update_fields=['actuator_status', 'updated_at'])
        return audit

    is_on = audit.pump_seconds > 0
    audit.device_command = enqueue_device_command(
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
    audit.command_created = True
    audit.actuator_status = AMPCRecommendation.ActuatorStatus.QUEUED
    audit.save(update_fields=[
        'device_command', 'command_created', 'actuator_status',
        'updated_at',
    ])
    notify_pending_commands()
    return audit


def run_auto_recommendation(
    *,
    create_command_if_auto: bool = True,
    user=None,
    owner=None,
) -> AMPCRecommendation:
    owner = owner or default_control_owner(user)
    profile = get_control_profile(owner=owner)
    now = timezone.now()

    try:
        config = profile_to_config(profile)
    except ValueError as exc:
        return _persist_failure(profile, f'invalid_fao_config:{exc}', status='config_error')

    estimation = _latest_estimation(owner, config, now)
    if estimation is None:
        return _persist_failure(profile, 'missing_estimation', config=config)
    state = _controller_state(estimation, owner)

    try:
        et0 = get_hourly_et0(now, step_seconds=config.step_seconds, owner=owner)
        config = profile_to_config(profile, et0_hour_mm=et0.et0_hour_mm)
    except OpenMeteoError as exc:
        return _persist_failure(
            profile, f'et0_unavailable:{exc}',
            config=config, estimation=estimation, state=state,
        )
    except ValueError as exc:
        return _persist_failure(profile, f'invalid_fao_config:{exc}', status='config_error')

    try:
        recommendation = ScipyMpcSolver(config).recommend(
            state=state,
            now=now,
        )
    except Exception as exc:
        recommendation = _failure(config, 'model_error', str(exc))

    audit = _persist(profile, config, recommendation, estimation=estimation, state=state, et0=et0)
    if create_command_if_auto and profile.actuator_enabled and audit.mode == ControlState.Mode.AUTO:
        return _queue_pump_command(audit)
    return audit
