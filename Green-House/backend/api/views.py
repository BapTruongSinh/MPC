from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    Alert,
    ControlState,
    DeviceCommand,
    DeviceState,
    EstimationCycle,
    EvaluationSummary,
    ExperimentRun,
    SensorData,
)
from .serializers import (
    AMPCRecommendationSerializer,
    AMPCSchedulerStateSerializer,
    AlertSerializer,
    ControlModeInputSerializer,
    ControlStateSerializer,
    DeviceCommandAckInputSerializer,
    DeviceCommandInputSerializer,
    DeviceCommandSerializer,
    DeviceStateSerializer,
    EstimationCycleSerializer,
    CycleSerializer,
    EvaluationSummarySerializer,
    GreenhouseControlProfileSerializer,
    IngestHeartbeatSerializer,
    IngestReadingSerializer,
    LegacyAMPCRecommendationSerializer,
    LiveSampleSerializer,
    LoginSerializer,
    RunListSerializer,
    SensorDataSerializer,
)
from .ampc import (
    get_greenhouse_control_profile,
    latest_recommendation,
    run_auto_recommendation,
)
from .ampc_scheduler import (
    get_scheduler_state,
    run_due_once,
    start_scheduler,
    stop_scheduler,
)
from .estimation import ensure_estimation_for_reading, latest_estimation
from .services import (
    ack_device_command_payload,
    build_uptime_hint,
    enqueue_device_command,
    get_pending_commands,
    ingest_heartbeat_payload,
    ingest_sensor_payload,
    is_esp32_online,
    notify_pending_commands,
)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'on', 'yes'}


def _legacy_auto_settings_payload(profile):
    return {
        'crop_name': profile.crop_name,
        'crop_kc': profile.crop_kc,
        'latitude': profile.latitude,
        'longitude': profile.longitude,
        'soil_type': profile.soil_type,
        'theta_fc': profile.theta_fc,
        'theta_wp': profile.theta_wp,
        'theta_sat': profile.theta_sat,
        'root_depth_m': profile.root_depth_m,
        'depletion_fraction_p': profile.depletion_fraction_p,
        'pump_efficiency': profile.pump_efficiency,
        'pump_flow_lps': profile.pump_flow_lps,
        'irrigation_area_m2': profile.irrigation_area_m2,
        'target_low': profile.target_low,
        'target_high': profile.target_high,
        'step_seconds': profile.step_seconds,
        'horizon_steps': profile.horizon_steps,
        'pump_min_seconds': profile.pump_min_seconds,
        'pump_max_seconds': profile.pump_max_seconds,
        'pump_grid_seconds': profile.pump_grid_seconds,
        'soft_daily_pump_cap_seconds': profile.soft_daily_pump_cap_seconds,
        'weight_band': profile.cost_band_violation,
        'weight_water': profile.cost_water_use,
        'weight_switch': profile.cost_switching,
        'weight_daily': profile.cost_daily_cap_excess,
        'weight_terminal': profile.cost_terminal_band_violation,
        'adaptive_enabled': profile.adaptive_enabled,
        'adaptive_bias_window': profile.adaptive_bias_window,
        'adaptive_max_abs_bias': profile.adaptive_max_abs_bias,
        'stale_after_seconds': profile.safety_stale_after_seconds,
        'actuator_enabled': profile.actuator_enabled,
        'updated_at': profile.updated_at,
    }


def _legacy_auto_settings_patch(data) -> dict:
    mapping = {
        'weight_band': 'cost_band_violation',
        'weight_water': 'cost_water_use',
        'weight_switch': 'cost_switching',
        'weight_daily': 'cost_daily_cap_excess',
        'weight_terminal': 'cost_terminal_band_violation',
        'stale_after_seconds': 'safety_stale_after_seconds',
    }
    allowed = {
        'crop_name', 'crop_kc', 'latitude', 'longitude', 'soil_type',
        'theta_fc', 'theta_wp', 'theta_sat', 'root_depth_m',
        'depletion_fraction_p', 'pump_efficiency', 'pump_flow_lps',
        'irrigation_area_m2', 'target_low', 'target_high',
        'step_seconds', 'horizon_steps', 'pump_min_seconds',
        'pump_max_seconds', 'pump_grid_seconds', 'soft_daily_pump_cap_seconds',
        'adaptive_enabled', 'adaptive_bias_window', 'adaptive_max_abs_bias',
        'actuator_enabled',
    }
    patch = {}
    for key, value in data.items():
        if key in mapping:
            patch[mapping[key]] = value
        elif key in allowed:
            patch[key] = value
    return patch


def _get_control_state():
    control, _ = ControlState.objects.get_or_create(singleton_key='main')
    return control


def _query_int(request, name: str, default: int, *, min_value: int, max_value: int) -> int:
    raw_value = request.query_params.get(name, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValidationError({name: f'{name} must be an integer'})
    return min(max(value, min_value), max_value)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer


class DashboardOverviewView(APIView):
    def get(self, request):
        esp32_online = is_esp32_online()
        latest = SensorData.objects.order_by('-recorded_at', '-id').first() if esp32_online else None
        recent_alerts = Alert.objects.order_by('-happened_at', '-id')[:5]
        control = _get_control_state()
        device_states = DeviceState.objects.exclude(device_code='esp32-main')

        payload = {
            'latest': SensorDataSerializer(latest).data if latest else None,
            'control': ControlStateSerializer(control).data,
            'device_states': DeviceStateSerializer(device_states, many=True).data,
            'unread_alerts': Alert.objects.filter(is_read=False).count(),
            'uptime_hint': build_uptime_hint(),
            'recent_alerts': AlertSerializer(recent_alerts, many=True).data,
            'esp32_online': esp32_online,
        }
        return Response(payload)


class LatestReadingView(APIView):
    def get(self, request):
        if not is_esp32_online():
            return Response(None)
        latest = SensorData.objects.order_by('-recorded_at', '-id').first()
        if not latest:
            return Response(None)
        return Response(SensorDataSerializer(latest).data)


class ChartView(APIView):
    def get(self, request):
        metric = request.query_params.get('metric')
        hours = _query_int(request, 'hours', 24, min_value=1, max_value=24 * 30)

        if metric not in {'temperature', 'humidity', 'light', 'soil_moisture'}:
            raise ValidationError('metric không hợp lệ')

        if not is_esp32_online():
            return Response({'metric': metric, 'points': []})

        since = timezone.now() - timedelta(hours=hours)
        points = []

        for item in SensorData.objects.filter(recorded_at__gte=since).order_by('recorded_at', 'id'):
            value = getattr(item, metric, None)
            points.append({'recorded_at': item.recorded_at, 'value': value})

        return Response({'metric': metric, 'points': points})


class SensorHistoryView(APIView):
    def get(self, request):
        page = _query_int(request, 'page', 1, min_value=1, max_value=1_000_000)
        page_size = _query_int(request, 'page_size', 20, min_value=5, max_value=100)

        queryset = SensorData.objects.order_by('-recorded_at', '-id')

        hours_raw = request.query_params.get('hours')
        date_from_raw = request.query_params.get('date_from')
        date_to_raw = request.query_params.get('date_to')

        if date_from_raw:
            date_from = parse_datetime(date_from_raw)
            if not date_from:
                raise ValidationError('date_from không hợp lệ')
            if timezone.is_naive(date_from):
                date_from = timezone.make_aware(date_from, timezone.get_current_timezone())
            queryset = queryset.filter(recorded_at__gte=date_from)

        if date_to_raw:
            date_to = parse_datetime(date_to_raw)
            if not date_to:
                raise ValidationError('date_to không hợp lệ')
            if timezone.is_naive(date_to):
                date_to = timezone.make_aware(date_to, timezone.get_current_timezone())
            queryset = queryset.filter(recorded_at__lte=date_to)

        if hours_raw and not date_from_raw and not date_to_raw:
            hours = _query_int(request, 'hours', 24, min_value=1, max_value=24 * 30)
            since = timezone.now() - timedelta(hours=hours)
            queryset = queryset.filter(recorded_at__gte=since)

        total = queryset.count()
        total_pages = max((total + page_size - 1) // page_size, 1)

        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        rows = queryset[start:end]

        return Response({
            'items': SensorDataSerializer(rows, many=True).data,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
        })


class ControlStateView(APIView):
    def get(self, request):
        control = _get_control_state()
        return Response(ControlStateSerializer(control).data)


class ControlModeView(APIView):
    def post(self, request):
        serializer = ControlModeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mode = data['mode']
        if mode not in {'AUTO', 'MANUAL'}:
            raise ValidationError('mode phải là AUTO hoặc MANUAL')

        control = _get_control_state()
        control.mode = mode
        control.manual_reason = data.get('reason') or ''

        if mode == ControlState.Mode.AUTO:
            control.manual_changed_at = None
            control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])
        else:
            control.manual_changed_at = timezone.now()
            control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])

        return Response(ControlStateSerializer(control).data)


class ForecastView(APIView):
    def get(self, request):
        estimation = latest_estimation()
        rec = latest_recommendation()
        scheduler_state = get_scheduler_state()

        latest_sensor = SensorData.objects.order_by('-recorded_at', '-id').first()
        use_estimation_history = (
            estimation is not None
            and (latest_sensor is None or estimation.sample_ts > latest_sensor.recorded_at)
        )
        if use_estimation_history:
            cycles = (
                EstimationCycle.objects
                .exclude(raw_soil_moisture__isnull=True)
                .exclude(raw_temperature__isnull=True)
                .exclude(raw_humidity__isnull=True)
                .exclude(raw_light__isnull=True)
                .order_by('-sample_ts', '-id')[:6]
            )
            history = [EstimationCycleSerializer(c).data for c in reversed(list(cycles))]
        else:
            history_rows = SensorData.objects.order_by('-recorded_at', '-id')[:6]
            history = [SensorDataSerializer(item).data for item in reversed(list(history_rows))]

        return Response({
            'latest': SensorDataSerializer(latest_sensor).data if latest_sensor else None,
            'estimation': EstimationCycleSerializer(estimation).data if estimation else None,
            'recommendation': AMPCRecommendationSerializer(rec).data if rec else None,
            'scheduler': AMPCSchedulerStateSerializer(scheduler_state).data,
            'history': history,
        })


class AutoSettingsView(APIView):
    def get(self, request):
        profile = get_greenhouse_control_profile()
        return Response(_legacy_auto_settings_payload(profile))

    def patch(self, request):
        profile = get_greenhouse_control_profile()
        serializer = GreenhouseControlProfileSerializer(
            profile,
            data=_legacy_auto_settings_patch(request.data),
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(_legacy_auto_settings_payload(profile))


class AutoRecommendationView(APIView):
    def post(self, request):
        recommendation = run_auto_recommendation(create_command_if_auto=True)
        status_code = status.HTTP_200_OK if recommendation.safety_status == 'safe' else status.HTTP_202_ACCEPTED
        return Response(AMPCRecommendationSerializer(recommendation).data, status=status_code)


class AMPCSchedulerView(APIView):
    def get(self, request):
        return Response(AMPCSchedulerStateSerializer(get_scheduler_state()).data)


class AMPCSchedulerStartView(APIView):
    def post(self, request):
        state = start_scheduler()
        state = run_due_once(force=True, state_id=state.id) or get_scheduler_state()
        return Response(AMPCSchedulerStateSerializer(state).data)


class AMPCSchedulerStopView(APIView):
    def post(self, request):
        state = stop_scheduler()
        return Response(AMPCSchedulerStateSerializer(state).data)


class RunListView(generics.ListAPIView):
    serializer_class = RunListSerializer

    def get_queryset(self):
        return (
            ExperimentRun.objects
            .order_by('-created_at', '-id')
        )


class RunSeriesView(APIView):
    def get(self, request, run_id: int):
        run = generics.get_object_or_404(ExperimentRun, pk=run_id)
        limit = _query_int(request, 'limit', 500, min_value=1, max_value=5000)
        cycles = (
            EstimationCycle.objects
            .filter(run=run)
            .order_by('-sample_ts', '-id')[:limit]
        )
        return Response(CycleSerializer(reversed(list(cycles)), many=True).data)


class RunMetricsView(APIView):
    def get(self, request, run_id: int):
        run = generics.get_object_or_404(ExperimentRun, pk=run_id)
        summary = EvaluationSummary.objects.filter(run=run).first()
        if summary is None:
            return Response({'detail': 'metrics_not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(EvaluationSummarySerializer(summary).data)


class ControlProfileView(APIView):
    """Endpoint để xem/sửa cấu hình điều khiển (singleton)."""
    def get(self, request):
        profile = get_greenhouse_control_profile()
        return Response(GreenhouseControlProfileSerializer(profile).data)

    def patch(self, request):
        profile = get_greenhouse_control_profile()
        serializer = GreenhouseControlProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AMPCLatestRecommendationView(APIView):
    def get(self, request):
        rec = latest_recommendation()
        if rec is None:
            return Response({'detail': 'recommendation_not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(LegacyAMPCRecommendationSerializer(rec).data)


class DeviceStateListView(generics.ListAPIView):
    """Danh sách trạng thái các thiết bị (pump, fan, mist, light)."""
    serializer_class = DeviceStateSerializer

    def get_queryset(self):
        return DeviceState.objects.exclude(device_code='esp32-main').order_by('device_code')


class DeviceToggleView(APIView):
    """Bật/tắt thiết bị theo device_code."""
    def post(self, request, device_code: str):
        if device_code not in {'fan', 'pump', 'light', 'mist'}:
            raise ValidationError('device_code không hợp lệ. Phải là: fan, pump, light, mist')

        control = _get_control_state()
        control.mode = ControlState.Mode.MANUAL
        control.manual_reason = f'manual_toggle:{device_code}'
        control.manual_changed_at = timezone.now()
        control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])

        state, _ = DeviceState.objects.get_or_create(device_code=device_code)
        state.is_on = not state.is_on
        state.desired_on = state.is_on
        state.last_command = 'toggle'
        state.last_value = 'on' if state.is_on else 'off'
        state.save(update_fields=['is_on', 'desired_on', 'last_command', 'last_value', 'updated_at'])

        enqueue_device_command(device_code=device_code, command='set_power', value=state.last_value)
        notify_pending_commands()
        return Response(DeviceStateSerializer(state).data)


class DeviceCommandView(APIView):
    """Gửi lệnh tới thiết bị theo device_code."""
    def post(self, request, device_code: str):
        serializer = DeviceCommandInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if device_code not in {'fan', 'pump', 'light', 'mist'}:
            raise ValidationError('device_code không hợp lệ. Phải là: fan, pump, light, mist')

        command = data['command']
        payload = data.get('payload') or {}
        value = data.get('value') or ''

        if not command:
            raise ValidationError('Thiếu command')

        control = _get_control_state()
        control.mode = ControlState.Mode.MANUAL
        control.manual_reason = f'manual_command:{device_code}:{command}'
        control.manual_changed_at = timezone.now()
        control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])

        cmd = enqueue_device_command(
            device_code=device_code,
            command=command,
            value=value,
            payload=payload,
        )

        state, _ = DeviceState.objects.get_or_create(device_code=device_code)
        state.last_command = command

        if value:
            state.last_value = value
            if value.lower() in {'on', 'off'}:
                state.desired_on = value.lower() == 'on'

        state.save(update_fields=['last_command', 'last_value', 'desired_on', 'updated_at'])
        notify_pending_commands()
        return Response(DeviceCommandSerializer(cmd).data, status=status.HTTP_201_CREATED)


class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer

    def get_queryset(self):
        return Alert.objects.order_by('-happened_at', '-id')


class AlertMarkReadView(APIView):
    def post(self, request, pk: int):
        alert = generics.get_object_or_404(Alert, pk=pk)
        alert.is_read = True
        alert.save(update_fields=['is_read', 'updated_at'])
        return Response(AlertSerializer(alert).data)


class AlertMarkAllReadView(APIView):
    def post(self, request):
        updated = Alert.objects.filter(is_read=False).update(is_read=True, updated_at=timezone.now())
        return Response({'updated': updated})


class LiveIngestSamplesView(APIView):
    """Ingest live sample từ thiết bị (không cần Device token nữa)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LiveSampleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        run = generics.get_object_or_404(ExperimentRun, pk=data['run_id'])

        payload = {
            'source': 'live_sample',
            'drip': data.get('drip'),
            'mist': data.get('mist'),
            'fan': data.get('fan'),
        }
        reading = SensorData.objects.create(
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            light=data.get('light'),
            soil_moisture=data.get('soil_moisture'),
            payload=payload,
            recorded_at=data['timestamp'],
        )
        estimation = ensure_estimation_for_reading(reading, run=run)

        return Response({
            'id': estimation.id,
            'run_id': run.id,
            'cycle_index': estimation.cycle_index,
            'preprocess_status': estimation.preprocess_status,
            'cycle_status': estimation.cycle_status,
            'adaptive_status': estimation.adaptive_status,
            'kf_x_posterior': estimation.kf_x_posterior,
            'kf_innovation': estimation.kf_innovation,
            'sample_ts': estimation.sample_ts,
        }, status=status.HTTP_201_CREATED)


class IngestReadingsView(APIView):
    """Nhận dữ liệu cảm biến từ ESP32 qua HTTP (không cần token device)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = IngestReadingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {**request.data, **serializer.validated_data}
        reading = ingest_sensor_payload(payload)
        estimation = ensure_estimation_for_reading(reading)

        return Response({
            'id': reading.id,
            'estimation_id': estimation.id,
            'message': 'Đã nhận dữ liệu cảm biến',
        })


class IngestHeartbeatView(APIView):
    """Nhận heartbeat từ ESP32 qua HTTP (không cần token device)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = IngestHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {**request.data, **serializer.validated_data}
        ingest_heartbeat_payload(payload)
        return Response({'message': 'heartbeat ok'})


class IngestPendingCommandsView(APIView):
    """ESP32 kéo danh sách lệnh đang chờ."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        device_code = request.query_params.get('device_code', 'esp32-main')
        commands = get_pending_commands(device_code=device_code)
        return Response(commands)


class IngestCommandAckView(APIView):
    """ESP32 xác nhận đã thực hiện lệnh."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk: int):
        serializer = DeviceCommandAckInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {**serializer.validated_data, 'id': pk}
        cmd = ack_device_command_payload(payload)
        if cmd is None:
            raise Http404('command_not_found')

        return Response({'message': 'ack ok'})


class DeviceCommandHistoryView(APIView):
    def get(self, request):
        page = _query_int(request, 'page', 1, min_value=1, max_value=1_000_000)
        page_size = _query_int(request, 'page_size', 20, min_value=5, max_value=100)

        queryset = DeviceCommand.objects.order_by('-created_at', '-id')

        total = queryset.count()
        total_pages = max((total + page_size - 1) // page_size, 1)

        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        rows = queryset[start:end]

        return Response({
            'items': DeviceCommandSerializer(rows, many=True).data,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
        })
