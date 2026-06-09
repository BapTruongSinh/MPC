from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
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
    IngestReadingSerializer,
    LegacyAMPCRecommendationSerializer,
    LoginSerializer,
    RunListSerializer,
    SensorDataSerializer,
)
from .ampc import (
    default_greenhouse,
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
        'soft_daily_pump_cap_seconds': profile.soft_daily_pump_cap_seconds,
        'weight_band': profile.cost_band_violation,
        'weight_water': profile.cost_water_use,
        'weight_switch': profile.cost_switching,
        'weight_daily': profile.cost_daily_cap_excess,
        'weight_terminal': profile.cost_terminal_band_violation,
        'stale_after_seconds': profile.safety_stale_after_seconds,
        'actuator_enabled': profile.actuator_enabled,
        'updated_at': profile.updated_at,
    }


def _legacy_auto_settings_patch(data) -> dict:
    derived_fields = sorted(set(data) & {'theta_fc', 'theta_wp', 'pump_max_seconds'})
    if derived_fields:
        raise ValidationError({
            field: f'{field} is derived from other settings and cannot be set directly'
            for field in derived_fields
        })
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
        'root_depth_m', 'depletion_fraction_p', 'pump_efficiency', 'pump_flow_lps',
        'irrigation_area_m2', 'target_low', 'target_high',
        'step_seconds', 'horizon_steps', 'pump_min_seconds',
        'soft_daily_pump_cap_seconds', 'actuator_enabled',
    }
    patch = {}
    for key, value in data.items():
        if key in mapping:
            patch[mapping[key]] = value
        elif key in allowed:
            patch[key] = value
    if 'step_seconds' in patch:
        patch['pump_max_seconds'] = patch['step_seconds']
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


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class SetupStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        setup_required = not User.objects.exists()
        return Response({'setup_required': setup_required})


class SetupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if User.objects.exists():
            return Response({'detail': 'Setup already completed'}, status=status.HTTP_400_BAD_REQUEST)

        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'detail': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_superuser(username=username, password=password, email='')
        return Response({'detail': 'Admin account created successfully'})


class DashboardOverviewView(APIView):
    def get(self, request):
        greenhouse = default_greenhouse(request.user)
        esp32_online = is_esp32_online()
        latest = (
            SensorData.objects
            .filter(greenhouse=greenhouse)
            .order_by('-recorded_at', '-id')
            .first()
            if esp32_online
            else None
        )
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
        greenhouse = default_greenhouse(request.user)
        latest = (
            SensorData.objects
            .filter(greenhouse=greenhouse)
            .order_by('-recorded_at', '-id')
            .first()
        )
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

        greenhouse = default_greenhouse(request.user)
        since = timezone.now() - timedelta(hours=hours)
        points = []

        for item in (
            SensorData.objects
            .filter(greenhouse=greenhouse, recorded_at__gte=since)
            .order_by('recorded_at', 'id')
        ):
            value = getattr(item, metric, None)
            points.append({'recorded_at': item.recorded_at, 'value': value})

        return Response({'metric': metric, 'points': points})


class SensorHistoryView(APIView):
    def get(self, request):
        greenhouse = default_greenhouse(request.user)
        page = _query_int(request, 'page', 1, min_value=1, max_value=1_000_000)
        page_size = _query_int(request, 'page_size', 20, min_value=5, max_value=100)

        queryset = SensorData.objects.filter(greenhouse=greenhouse).order_by('-recorded_at', '-id')

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


def _forecast_history_from_cycle(cycle: EstimationCycle) -> dict:
    return {
        'id': cycle.id,
        'temperature': cycle.raw_temperature,
        'humidity': cycle.raw_humidity,
        'light': cycle.raw_light,
        'soil_moisture': cycle.raw_soil_moisture,
        'payload': {'source': cycle.source_type},
        'recorded_at': cycle.sample_ts,
    }


def _sampled_sensor_history_rows(greenhouse, rec, latest_sensor):
    if latest_sensor is None:
        return []

    step_seconds = int(getattr(rec, 'step_seconds', None) or 300)
    step_seconds = max(1, step_seconds)
    anchor = getattr(getattr(rec, 'estimation', None), 'sample_ts', None) or latest_sensor.recorded_at
    rows = []

    for index in range(5, -1, -1):
        target_ts = anchor - timedelta(seconds=step_seconds * index)
        window_start = target_ts - timedelta(seconds=step_seconds)
        reading = (
            SensorData.objects
            .filter(
                greenhouse=greenhouse,
                recorded_at__gt=window_start,
                recorded_at__lte=target_ts,
            )
            .order_by('-recorded_at', '-id')
            .first()
        )
        if reading is not None:
            rows.append(SensorDataSerializer(reading).data)
    return rows


def _forecast_history_rows(greenhouse, rec):
    latest_sensor = (
        SensorData.objects
        .filter(greenhouse=greenhouse)
        .order_by('-recorded_at', '-id')
        .first()
    )
    sensor_rows = _sampled_sensor_history_rows(greenhouse, rec, latest_sensor)
    if sensor_rows:
        return sensor_rows

    anchor = getattr(rec, 'estimation', None) if rec is not None else None
    if anchor is not None and anchor.source_type == 'live_window':
        cycles = (
            EstimationCycle.objects
            .filter(
                greenhouse=greenhouse,
                source_type='live_window',
                sample_ts__lte=anchor.sample_ts,
            )
            .exclude(raw_soil_moisture__isnull=True)
            .exclude(raw_temperature__isnull=True)
            .exclude(raw_humidity__isnull=True)
            .exclude(raw_light__isnull=True)
            .order_by('-sample_ts', '-id')[:6]
        )
        return [_forecast_history_from_cycle(cycle) for cycle in reversed(list(cycles))]

    history_rows = (
        SensorData.objects
        .filter(greenhouse=greenhouse)
        .order_by('-recorded_at', '-id')[:6]
    )
    return [SensorDataSerializer(item).data for item in reversed(list(history_rows))]


class ForecastView(APIView):
    def get(self, request):
        greenhouse = default_greenhouse(request.user)
        estimation = latest_estimation(greenhouse=greenhouse)
        rec = latest_recommendation(greenhouse=greenhouse)
        scheduler_state = get_scheduler_state()

        latest_sensor = (
            SensorData.objects
            .filter(greenhouse=greenhouse)
            .order_by('-recorded_at', '-id')
            .first()
        )

        return Response({
            'latest': SensorDataSerializer(latest_sensor).data if latest_sensor else None,
            'estimation': EstimationCycleSerializer(estimation).data if estimation else None,
            'recommendation': AMPCRecommendationSerializer(rec).data if rec else None,
            'scheduler': AMPCSchedulerStateSerializer(scheduler_state).data,
            'history': _forecast_history_rows(greenhouse, rec),
        })


class AutoSettingsView(APIView):
    def get(self, request):
        profile = get_greenhouse_control_profile(request.user)
        return Response(_legacy_auto_settings_payload(profile))

    def patch(self, request):
        profile = get_greenhouse_control_profile(request.user)
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
        recommendation = run_auto_recommendation(
            create_command_if_auto=True,
            user=request.user,
        )
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
    """Endpoint de xem/sua cau hinh dieu khien theo greenhouse cua user."""
    def get(self, request):
        profile = get_greenhouse_control_profile(request.user)
        return Response(GreenhouseControlProfileSerializer(profile).data)

    def patch(self, request):
        profile = get_greenhouse_control_profile(request.user)
        serializer = GreenhouseControlProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AMPCLatestRecommendationView(APIView):
    def get(self, request):
        greenhouse = default_greenhouse(request.user)
        rec = latest_recommendation(greenhouse=greenhouse)
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


class TelegramSettingsView(APIView):
    """GET trạng thái Telegram, PATCH cập nhật token/chat_id vào .env."""
    _ENV_PATH = Path(settings.BASE_DIR) / '.env'

    def _read_env(self):
        path = self._ENV_PATH
        return path.read_text(encoding='utf-8') if path.exists() else ''

    def _write_env(self, content: str):
        self._ENV_PATH.write_text(content, encoding='utf-8')

    def _set_env_var(self, content: str, key: str, value: str) -> str:
        pattern = re.compile(r'^' + re.escape(key) + r'=.*$', re.MULTILINE)
        replacement = f'{key}={value}'
        if pattern.search(content):
            return pattern.sub(replacement, content)
        # Thêm vào cuối file nếu chưa có
        return content.rstrip('\n') + f'\n{replacement}\n'

    def get(self, request):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '') or ''
        return Response({
            'token_configured': bool(token),
            'chat_id_configured': bool(chat_id),
            'chat_id': chat_id,
        })

    def patch(self, request):
        import importlib
        import os
        from dotenv import load_dotenv

        token = request.data.get('telegram_bot_token', '').strip()
        chat_id = request.data.get('telegram_chat_id', '').strip()

        if not token and not chat_id:
            raise ValidationError('Phải cung cấp ít nhất telegram_bot_token hoặc telegram_chat_id')

        content = self._read_env()
        if token:
            content = self._set_env_var(content, 'TELEGRAM_BOT_TOKEN', token)
        if chat_id:
            content = self._set_env_var(content, 'TELEGRAM_CHAT_ID', chat_id)
        self._write_env(content)

        # Reload env vào os.environ và Django settings ngay lập tức
        load_dotenv(self._ENV_PATH, override=True)
        if token:
            settings.TELEGRAM_BOT_TOKEN = token
        if chat_id:
            settings.TELEGRAM_CHAT_ID = chat_id

        return Response({'detail': 'Đã cập nhật cấu hình Telegram thành công.', 'chat_id': chat_id})


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
