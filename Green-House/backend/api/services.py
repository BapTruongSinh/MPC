from __future__ import annotations

from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from .models import Alert, ControlState, DeviceCommand, DeviceState, SensorData
from .serializers import (
    COMMAND_STATUS_VALUES,
    DEVICE_COMMAND_TEXT_MAX_LENGTH,
    KNOWN_SENSOR_ERROR_KEYS,
    MANUAL_REASON_MAX_LENGTH,
    DeviceCommandSerializer,
    validate_json_finite,
    validate_sensor_numeric_fields,
)

# ── Hằng số heartbeat (kiểm tra bằng RAM, không cần DB Device) ──
HEARTBEAT_TIMEOUT_SECONDS = 15
HEARTBEAT_SLOW_SECONDS = 30

# Trạng thái kết nối ESP32 lưu trong RAM (thay vì DB Device)
_esp32_last_seen: dict[str, object] = {}  # device_code -> datetime


def _clean_limited_text(field: str, value, max_length: int) -> str:
    if value is None:
        return ''
    text = str(value).strip()
    if len(text) > max_length:
        raise ValidationError({field: f'{field} must be at most {max_length} characters'})
    return text


def _clean_sensor_errors(value) -> dict:
    if value in (None, ''):
        return {}
    if not isinstance(value, dict):
        raise ValidationError({'sensor_errors': 'sensor_errors must be an object'})

    unknown = sorted(str(key) for key in value.keys() if str(key) not in KNOWN_SENSOR_ERROR_KEYS)
    if unknown:
        raise ValidationError({
            'sensor_errors': f"sensor_errors only supports keys: {', '.join(sorted(KNOWN_SENSOR_ERROR_KEYS))}"
        })
    return validate_json_finite(value, 'sensor_errors')


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'on', 'yes'}


def _push_ws_group(group_name: str, event_type: str, data: dict):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'ws_message',
            'event_type': event_type,
            'data': data,
        },
    )


# ── ESP32 online/offline theo RAM (thay vì DB Device) ──

def mark_esp32_online(device_code: str = 'esp32-main'):
    """Cập nhật thời gian last_seen cho ESP32 trong RAM."""
    _esp32_last_seen[device_code] = timezone.now()


def mark_device_offline(device_code: str = 'esp32-main'):
    """Đánh dấu ESP32 đã offline (xóa khỏi RAM cache)."""
    _esp32_last_seen.pop(device_code, None)


def is_esp32_online(device_code: str = 'esp32-main') -> bool:
    """Kiểm tra ESP32 có đang online không dựa trên last_seen trong RAM."""
    last_seen = _esp32_last_seen.get(device_code)
    if last_seen is None:
        return False
    return (timezone.now() - last_seen).total_seconds() <= HEARTBEAT_TIMEOUT_SECONDS


def build_uptime_hint(device_code: str = 'esp32-main') -> str:
    last_seen = _esp32_last_seen.get(device_code)
    if not last_seen:
        return 'Chưa có heartbeat từ ESP32'
    delta = timezone.now() - last_seen
    if delta.total_seconds() <= HEARTBEAT_TIMEOUT_SECONDS:
        return 'ESP32 đang online'
    if delta.total_seconds() <= HEARTBEAT_SLOW_SECONDS:
        return 'ESP32 phản hồi chậm'
    return 'ESP32 đang mất kết nối'


def get_pending_commands(limit: int = 5, *, device_code: str | None = None):
    queryset = (
        DeviceCommand.objects
        .filter(status=DeviceCommand.CommandStatus.PENDING)
    )
    if device_code is not None:
        queryset = queryset.filter(device_code=device_code)

    commands = queryset.order_by('-updated_at', '-id')[:limit]
    return DeviceCommandSerializer(list(reversed(commands)), many=True).data


def notify_pending_commands(device_code: str = 'esp32-main'):
    data = {'commands': get_pending_commands()}
    _push_ws_group(f'esp32.{device_code}', 'pending_commands', data)


def _force_manual_mode(reason: str):
    reason = _clean_limited_text('manual_reason', reason, MANUAL_REASON_MAX_LENGTH)
    control, _ = ControlState.objects.get_or_create(singleton_key='main')

    if control.mode == ControlState.Mode.MANUAL and control.manual_reason == reason:
        return control

    control.mode = ControlState.Mode.MANUAL
    control.manual_reason = reason
    control.manual_changed_at = timezone.now()
    control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])
    return control


def sync_control_mode_from_payload(payload: dict):
    control, _ = ControlState.objects.get_or_create(singleton_key='main')

    sensor_errors = _clean_sensor_errors(payload.get('sensor_errors'))
    if bool(sensor_errors.get('dht', False)):
        return _force_manual_mode('dht_sensor_error')

    mode = payload.get('mode')
    auto_mode = payload.get('auto_mode')

    resolved_mode = None

    if isinstance(mode, str):
        mode = mode.strip().upper()
        if mode in {ControlState.Mode.AUTO, ControlState.Mode.MANUAL}:
            resolved_mode = mode

    if resolved_mode is None and auto_mode is not None:
        resolved_mode = ControlState.Mode.AUTO if _to_bool(auto_mode) else ControlState.Mode.MANUAL

    if resolved_mode is None:
        return control

    if control.mode != resolved_mode:
        control.mode = resolved_mode

        if resolved_mode == ControlState.Mode.AUTO:
            control.manual_reason = ''
            control.manual_changed_at = None
            control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])
        else:
            control.manual_reason = _clean_limited_text(
                'manual_reason',
                payload.get('manual_reason') or 'esp_button_mode',
                MANUAL_REASON_MAX_LENGTH,
            )
            control.manual_changed_at = timezone.now()
            control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])

    return control


def sync_sensor_alerts(payload: dict, device_code: str = 'esp32-main'):
    # Lưu sensor_errors vào metadata của DeviceState esp32-main
    state, _ = DeviceState.objects.get_or_create(device_code=device_code)
    metadata = state.extra or {}

    previous_errors = metadata.get('sensor_errors') or {}
    current_errors = _clean_sensor_errors(payload.get('sensor_errors'))

    changed = False

    for sensor_name, current_value in current_errors.items():
        current_value = bool(current_value)
        previous_value = bool(previous_errors.get(sensor_name, False))

        if current_value == previous_value:
            continue

        changed = True

    if bool(current_errors.get('dht', False)):
        _force_manual_mode('dht_sensor_error')

    if changed:
        metadata['sensor_errors'] = current_errors
        state.extra = metadata
        state.save(update_fields=['extra', 'updated_at'])

ALERT_PERSISTENCE_SECONDS = 300
MANUAL_IDLE_SECONDS = 3600

def check_environmental_alerts(payload: dict, device_code: str = 'esp32-main'):
    state, _ = DeviceState.objects.get_or_create(device_code=device_code)
    extra = state.extra or {}
    tracking = extra.get('alert_tracking') or {}
    
    now = timezone.now().timestamp()
    changed = False

    temp = payload.get('temperature')
    if temp is not None:
        try:
            temp = float(temp)
            if temp > 40.0 or temp < 10.0:
                if 'temp_alert_start' not in tracking:
                    tracking['temp_alert_start'] = now
                    changed = True
                elif not tracking.get('temp_alert_sent'):
                    if now - tracking['temp_alert_start'] >= ALERT_PERSISTENCE_SECONDS:
                        Alert.objects.create(
                            level=Alert.Level.WARNING,
                            device_code=device_code,
                            title='Cảnh báo Nhiệt độ cực đoan',
                            message=f'Nhiệt độ hiện tại là {temp}°C, kéo dài liên tục quá {ALERT_PERSISTENCE_SECONDS//60} phút.',
                        )
                        tracking['temp_alert_sent'] = True
                        changed = True
            else:
                if 'temp_alert_start' in tracking:
                    tracking.pop('temp_alert_start', None)
                    tracking.pop('temp_alert_sent', None)
                    changed = True
        except (ValueError, TypeError):
            pass

    soil = payload.get('soil_moisture')
    device_states = payload.get('device_states') or {}
    pump_on = _to_bool(device_states.get('pump_on', False))
    
    if soil is not None:
        try:
            soil = float(soil)
            if soil < 15.0 and not pump_on:
                if 'soil_alert_start' not in tracking:
                    tracking['soil_alert_start'] = now
                    changed = True
                elif not tracking.get('soil_alert_sent'):
                    if now - tracking['soil_alert_start'] >= ALERT_PERSISTENCE_SECONDS:
                        Alert.objects.create(
                            level=Alert.Level.ERROR,
                            device_code=device_code,
                            title='Cảnh báo Đất khô hạn',
                            message=f'Độ ẩm đất là {soil}%. Đất rất khô nhưng máy bơm chưa bật trong {ALERT_PERSISTENCE_SECONDS//60} phút qua.',
                        )
                        tracking['soil_alert_sent'] = True
                        changed = True
            else:
                if 'soil_alert_start' in tracking:
                    tracking.pop('soil_alert_start', None)
                    tracking.pop('soil_alert_sent', None)
                    changed = True
        except (ValueError, TypeError):
            pass

    control, _ = ControlState.objects.get_or_create(singleton_key='main')
    if control.mode == ControlState.Mode.MANUAL and control.manual_changed_at:
        idle_seconds = now - control.manual_changed_at.timestamp()
        if idle_seconds >= MANUAL_IDLE_SECONDS:
            if not tracking.get('manual_idle_alert_sent'):
                Alert.objects.create(
                    level=Alert.Level.WARNING,
                    device_code=device_code,
                    title='Quên bật chế độ AUTO',
                    message=f'Hệ thống đang ở chế độ thủ công (MANUAL) hơn {MANUAL_IDLE_SECONDS//60} phút mà không có thao tác nào. Bạn có quên bật lại AUTO không?',
                )
                tracking['manual_idle_alert_sent'] = True
                changed = True
        else:
            if tracking.pop('manual_idle_alert_sent', None):
                changed = True
    else:
        if tracking.pop('manual_idle_alert_sent', None):
            changed = True

    if changed:
        extra['alert_tracking'] = tracking
        state.extra = extra
        state.save(update_fields=['extra', 'updated_at'])


def ingest_sensor_payload(payload: dict, device_code: str = 'esp32-main'):
    validate_sensor_numeric_fields(payload)
    sensor_payload = validate_json_finite(payload.get('payload') or {}, 'payload')
    metadata = validate_json_finite(payload.get('metadata') or {}, 'metadata')
    sensor_errors = _clean_sensor_errors(payload.get('sensor_errors'))
    device_states = validate_json_finite(payload.get('device_states') or {}, 'device_states')
    firmware_version = _clean_limited_text(
        'firmware_version',
        payload.get('firmware_version'),
        50,
    )
    manual_reason = _clean_limited_text(
        'manual_reason',
        payload.get('manual_reason'),
        MANUAL_REASON_MAX_LENGTH,
    )
    payload = {**payload}
    payload['payload'] = sensor_payload
    payload['metadata'] = metadata
    payload['sensor_errors'] = sensor_errors
    payload['device_states'] = device_states
    if firmware_version:
        payload['firmware_version'] = firmware_version
    if manual_reason:
        payload['manual_reason'] = manual_reason

    recorded_raw = payload.get('recorded_at')
    recorded_at = parse_datetime(recorded_raw) if isinstance(recorded_raw, str) else recorded_raw
    recorded_at = recorded_at or timezone.now()

    reading = SensorData.objects.create(
        temperature=payload.get('temperature'),
        humidity=payload.get('humidity'),
        light=payload.get('light'),
        soil_moisture=payload.get('soil_moisture'),
        payload=sensor_payload,
        recorded_at=recorded_at,
    )

    # Đánh dấu ESP32 online trong RAM
    mark_esp32_online(device_code)

    sync_control_mode_from_payload(payload)
    sync_sensor_alerts(payload, device_code=device_code)
    check_environmental_alerts(payload, device_code=device_code)

    # Đồng bộ trạng thái thiết bị từ device_states
    state_map = {
        'fan_on': 'fan',
        'pump_on': 'pump',
        'light_on': 'light',
        'mist_on': 'mist',
    }

    states = device_states
    for field_name, dev_code in state_map.items():
        if field_name not in states:
            continue

        current_value = _to_bool(states[field_name])

        state, _ = DeviceState.objects.get_or_create(device_code=dev_code)
        state.is_on = current_value
        state.desired_on = current_value
        state.last_command = 'telemetry_sync'
        state.last_value = 'on' if current_value else 'off'
        state.save(update_fields=['is_on', 'desired_on', 'last_command', 'last_value', 'updated_at'])

    return reading



def enqueue_device_command(device_code: str, command: str, value: str = '', payload: dict | None = None):
    command = _clean_limited_text('command', command, DEVICE_COMMAND_TEXT_MAX_LENGTH)
    value = _clean_limited_text('value', value, DEVICE_COMMAND_TEXT_MAX_LENGTH)
    payload = validate_json_finite(payload or {}, 'payload')
    cmd = DeviceCommand.objects.create(
        device_code=device_code,
        command=command,
        value=value,
        payload=payload,
    )
    return cmd


def ack_device_command_payload(payload: dict, *, device_code: str | None = None):
    command_id = payload.get('id') or payload.get('command_id')
    if not command_id:
        return None

    queryset = DeviceCommand.objects
    if device_code is not None:
        queryset = queryset.filter(device_code=device_code)

    try:
        cmd = queryset.get(pk=command_id)
    except DeviceCommand.DoesNotExist:
        return None

    next_status = payload.get('status') or DeviceCommand.CommandStatus.ACK
    if next_status not in COMMAND_STATUS_VALUES:
        raise ValidationError({'status': f"status must be one of: {', '.join(COMMAND_STATUS_VALUES)}"})

    cmd.status = next_status
    cmd.acked_at = timezone.now()
    cmd.save(update_fields=['status', 'acked_at', 'updated_at'])

    state, _ = DeviceState.objects.get_or_create(device_code=cmd.device_code)

    actual_state = payload.get('actual_state')
    if actual_state is not None:
        actual_on = _to_bool(actual_state)
        state.is_on = actual_on
    else:
        actual_on = str(cmd.value).lower() == 'on'
        state.is_on = actual_on

    state.desired_on = actual_on
    state.last_command = cmd.command
    state.last_value = cmd.value
    state.save(update_fields=['is_on', 'desired_on', 'last_command', 'last_value', 'updated_at'])

    return cmd
