import asyncio
import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Alert, ControlState, DeviceState, SensorData
from .serializers import (
    AlertSerializer,
    ControlStateSerializer,
    DeviceStateSerializer,
    SensorDataSerializer,
)
from .services import (
    ack_device_command_payload,
    enqueue_device_command,
    get_pending_commands,
    ingest_sensor_payload,
    is_esp32_online,
    mark_device_offline,
)
from .user_resources import default_owner, ensure_user_control_profile

FRONTEND_POLL_SECONDS = 3
FRONTEND_GROUP = 'frontend.main'
ESP_GROUP = 'esp32.main'


def _control_state():
    control, _ = ControlState.objects.get_or_create(singleton_key='main')
    return control


def _current_sensor_errors() -> dict:
    """Lấy sensor_errors từ extra của DeviceState esp32-main."""
    state = DeviceState.objects.filter(device_code='esp32-main').first()
    sensor_errors = (state.extra or {}).get('sensor_errors') or {} if state else {}
    return {
        'dht': bool(sensor_errors.get('dht', False)),
        'soil': bool(sensor_errors.get('soil', False)),
        'light': bool(sensor_errors.get('light', False)),
        'gas': bool(sensor_errors.get('gas', False)),
    }


def _coerce_number(value, default=0):
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _sun_tracker_snapshot() -> dict:
    owner = default_owner()
    latest = (
        SensorData.objects
        .filter(owner=owner)
        .order_by('-recorded_at', '-id')
        .first()
    )

    payload = latest.payload if latest and isinstance(latest.payload, dict) else {}
    sun = payload.get('sun_tracker') if isinstance(payload.get('sun_tracker'), dict) else {}

    return {
        'mode': 'sun_auto' if sun.get('mode') == 'sun_auto' else 'sun_manual',
        'ldr_lt': _coerce_number(sun.get('ldr_lt'), 0),
        'ldr_rt': _coerce_number(sun.get('ldr_rt'), 0),
        'ldr_ld': _coerce_number(sun.get('ldr_ld'), 0),
        'ldr_rd': _coerce_number(sun.get('ldr_rd'), 0),
        'servo_vertical': int(_coerce_number(sun.get('servo_vertical'), 90)),
        'servo_horizontal': int(_coerce_number(sun.get('servo_horizontal'), 90)),
        'updated_at': latest.recorded_at.isoformat() if latest else None,
    }


def _device_states_payload() -> list:
    states = DeviceState.objects.exclude(device_code='esp32-main').order_by('device_code')
    return DeviceStateSerializer(states, many=True).data


def _dashboard_packet() -> dict:
    owner = default_owner()
    control = _control_state()
    esp32_online = is_esp32_online()
    sensor_errors = _current_sensor_errors()

    alerts = list(
        Alert.objects
        .order_by('-happened_at', '-id')[:20]
    )

    latest_data = None
    if esp32_online:
        latest = SensorData.objects.filter(owner=owner).order_by('-recorded_at', '-id').first()
        latest_data = SensorDataSerializer(latest).data if latest else None

    return {
        'type': 'state',
        'data': {
            'latest': latest_data,
            'control': ControlStateSerializer(control).data,
            'devices': _device_states_payload(),
            'alerts': AlertSerializer(alerts, many=True).data,
            'sensor_errors': sensor_errors,
            'esp32_online': esp32_online,
            'sun_tracker': _sun_tracker_snapshot(),
            'updated_at': timezone.now().isoformat(),
        },
    }


def _set_manual_mode(reason: str = ''):
    control = _control_state()
    control.mode = ControlState.Mode.MANUAL
    control.manual_reason = reason
    control.manual_changed_at = timezone.now()
    control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])


def _set_mode(mode: str):
    control = _control_state()
    mode = mode.upper().strip()

    if mode not in {ControlState.Mode.AUTO, ControlState.Mode.MANUAL}:
        raise ValueError('mode must be AUTO or MANUAL')

    if mode == ControlState.Mode.AUTO and _current_sensor_errors().get('dht', False):
        raise ValueError('cannot enable AUTO while DHT sensor is in error')

    control.mode = mode

    if mode == ControlState.Mode.AUTO:
        control.manual_reason = ''
        control.manual_changed_at = None
    else:
        control.manual_changed_at = timezone.now()
        if not control.manual_reason:
            control.manual_reason = 'frontend_mode_change'

    control.save(update_fields=['mode', 'manual_reason', 'manual_changed_at', 'updated_at'])


def auth_frontend_token_sync(token: str | None):
    if not token:
        return None

    try:
        authenticator = JWTAuthentication()
        validated = authenticator.get_validated_token(token)
        user = authenticator.get_user(validated)
    except Exception:
        return None

    if not user or not user.is_authenticated:
        return None

    return {'user_id': user.id}


@database_sync_to_async
def auth_frontend_token(token: str | None):
    return auth_frontend_token_sync(token)


@database_sync_to_async
def frontend_scope_for_user(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    return {'user_id': user.id}


@database_sync_to_async
def build_state_packet():
    return _dashboard_packet()


@database_sync_to_async
def ingest_telemetry(data: dict):
    ingest_sensor_payload(data)



@database_sync_to_async
def ack_command(data: dict):
    return ack_device_command_payload(data)


@database_sync_to_async
def pending_commands():
    return get_pending_commands()


@database_sync_to_async
def queue_manual_command(device_code: str, state: str, duration: int = 0):
    if device_code not in {'fan', 'pump', 'light', 'mist'}:
        raise ValueError(f'device not found: {device_code}')
    _set_manual_mode(reason=f'manual_ws:{device_code}')
    payload = None
    if duration > 0 and state.lower() == 'on':
        payload = {'duration': duration}
    enqueue_device_command(device_code=device_code, command='set_power', value=state.lower(), payload=payload)


@database_sync_to_async
def update_mode_only(mode: str):
    _set_mode(mode)


@database_sync_to_async
def update_sun_payload_snapshot(patch: dict):
    latest = SensorData.objects.filter(owner=default_owner()).order_by('-recorded_at', '-id').first()
    if latest is None:
        return

    payload = latest.payload if isinstance(latest.payload, dict) else {}
    sun = payload.get('sun_tracker') if isinstance(payload.get('sun_tracker'), dict) else {}

    payload['sun_tracker'] = {**sun, **patch}
    latest.payload = payload
    latest.save(update_fields=['payload'])


@database_sync_to_async
def do_mark_device_offline(device_code: str):
    mark_device_offline(device_code)


@database_sync_to_async
def get_threshold_config() -> dict:
    """Lấy ngưỡng ESP32 từ profile."""
    profile = ensure_user_control_profile(default_owner())
    return {
        'thresh_temp_fan_on': profile.thresh_temp_fan_on,
        'thresh_temp_fan_off': profile.thresh_temp_fan_off,
        'thresh_hum_fan_on': profile.thresh_hum_fan_on,
        'thresh_hum_fan_off': profile.thresh_hum_fan_off,
        'thresh_hum_mist_on': profile.thresh_hum_mist_on,
        'thresh_hum_mist_off': profile.thresh_hum_mist_off,
        'thresh_soil_pump_on': profile.thresh_soil_pump_on,
        'thresh_soil_pump_off': profile.thresh_soil_pump_off,
        'thresh_light_on_ldr': profile.thresh_light_on_ldr,
        'thresh_light_off_ldr': profile.thresh_light_off_ldr,
    }


class FrontendConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.monitor_task = None
        self.last_esp32_online = None

        raw_qs = (self.scope.get('query_string') or b'').decode()
        token = parse_qs(raw_qs).get('token', [None])[0]

        scope = await frontend_scope_for_user(self.scope.get('user'))

        if scope is None:
            scope = await auth_frontend_token(token)

        if scope is None:
            await self.close(code=4003)
            return

        self.group_name = FRONTEND_GROUP

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        packet = await build_state_packet()
        packet['type'] = 'bootstrap'
        self.last_esp32_online = packet['data'].get('esp32_online')

        await self.send(text_data=json.dumps(packet, cls=DjangoJSONEncoder))
        self.monitor_task = asyncio.create_task(self.monitor_status_changes())

    async def disconnect(self, close_code):
        if self.monitor_task:
            self.monitor_task.cancel()

            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'reason': 'invalid_json'}))
            return

        msg_type = payload.get('type')

        try:
            if msg_type == 'mode':
                mode_value = str(payload.get('value') or '').upper().strip()
                await update_mode_only(mode_value)

                # Đẩy lệnh mode sang ESP32
                await self.channel_layer.group_send(
                    ESP_GROUP,
                    {
                        'type': 'ws_message',
                        'event_type': 'mode',
                        'data': {'value': mode_value},
                    },
                )

                await self.send_state({'packet': await build_state_packet()})
                return

            if msg_type == 'device_control':
                device = str(payload.get('device') or '').strip().lower()
                state = str(payload.get('state') or '').strip().lower()
                duration = _coerce_number(payload.get('duration'), 0)

                if device not in {'fan', 'pump', 'light', 'mist'} or state not in {'on', 'off'}:
                    raise ValueError('invalid device_control')

                await queue_manual_command(device, state, int(duration))

                commands = await pending_commands()
                await self.channel_layer.group_send(
                    ESP_GROUP,
                    {
                        'type': 'ws_message',
                        'event_type': 'pending_commands',
                        'data': {'commands': commands},
                    },
                )

                await self.send_state({'packet': await build_state_packet()})
                return

            if msg_type == 'sun_mode':
                mode = str(payload.get('mode') or '').strip().lower()

                if mode not in {'sun_auto', 'sun_manual'}:
                    raise ValueError('invalid sun mode')

                await update_sun_payload_snapshot({'mode': mode})

                await self.channel_layer.group_send(
                    ESP_GROUP,
                    {
                        'type': 'ws_message',
                        'event_type': 'sun_control',
                        'data': {
                            'command': 'set_mode',
                            'mode': mode,
                        },
                    },
                )

                await self.send_state({'packet': await build_state_packet()})
                return

            if msg_type == 'sun_servo_control':
                servo = str(payload.get('servo') or '').strip().lower()

                if servo not in {'vertical', 'horizontal'}:
                    raise ValueError('invalid sun servo')

                try:
                    angle = int(round(float(payload.get('angle'))))
                except (TypeError, ValueError):
                    raise ValueError('invalid sun servo angle')

                angle = max(0, min(180, angle))

                await update_sun_payload_snapshot(
                    {
                        'servo_vertical' if servo == 'vertical' else 'servo_horizontal': angle,
                        'mode': 'sun_manual',
                    },
                )

                await self.channel_layer.group_send(
                    ESP_GROUP,
                    {
                        'type': 'ws_message',
                        'event_type': 'sun_control',
                        'data': {
                            'command': 'set_servo',
                            'servo': servo,
                            'angle': angle,
                        },
                    },
                )

                await self.send_state({'packet': await build_state_packet()})
                return

            if msg_type in {'alert_mark_read', 'alert_mark_all_read'}:
                return

            await self.send(
                text_data=json.dumps({'type': 'error', 'reason': f'unsupported:{msg_type}'})
            )

        except Exception as exc:
            await self.send(text_data=json.dumps({'type': 'error', 'reason': str(exc)}))
            await self.send_state({'packet': await build_state_packet()})

    async def send_state(self, event):
        packet = event['packet']
        self.last_esp32_online = packet.get('data', {}).get('esp32_online')
        await self.send(text_data=json.dumps(packet, cls=DjangoJSONEncoder))

    async def monitor_status_changes(self):
        try:
            while True:
                await asyncio.sleep(FRONTEND_POLL_SECONDS)

                packet = await build_state_packet()
                current_online = packet['data'].get('esp32_online')

                if current_online != self.last_esp32_online:
                    self.last_esp32_online = current_online
                    await self.send(text_data=json.dumps(packet, cls=DjangoJSONEncoder))

        except asyncio.CancelledError:
            pass


class ESPConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho ESP32. Không cần auth token, kết nối trực tiếp."""

    async def connect(self):
        self.device_code = (
            self.scope.get('url_route', {}).get('kwargs', {}).get('device_code')
            or 'esp32-main'
        )
        self.group_name = ESP_GROUP

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send_pending_commands()
        await self.send_threshold_config()
        await self.push_state_to_frontend()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        await do_mark_device_offline(self.device_code)
        await self.push_state_to_frontend()

    async def receive(self, text_data):
        try:
            packet = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'invalid_json'}))
            return

        msg_type = packet.get('type')
        data = packet.get('data') or {}

        try:
            if msg_type == 'telemetry':
                await ingest_telemetry(data)
                await self.push_state_to_frontend()
                return

            if msg_type == 'ack':
                cmd = await ack_command(data)

                if cmd is None:
                    await self.send(
                        text_data=json.dumps({'type': 'error', 'message': 'command_not_found'})
                    )
                else:
                    await self.push_state_to_frontend()

                return

            if msg_type == 'sync_commands':
                await self.send_pending_commands()
                return

            await self.send(
                text_data=json.dumps({'type': 'error', 'message': f'unsupported_type:{msg_type}'})
            )

        except Exception as exc:
            await self.send(text_data=json.dumps({'type': 'error', 'message': str(exc)}))

    async def send_pending_commands(self):
        commands = await pending_commands()

        await self.send(
            text_data=json.dumps(
                {
                    'type': 'pending_commands',
                    'data': {
                        'commands': commands,
                    },
                }
            )
        )

    async def send_threshold_config(self):
        """Gửi ngưỡng điều khiển xuống ESP32 ngay khi kết nối."""
        thresholds = await get_threshold_config()
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'threshold_config',
                    'data': thresholds,
                }
            )
        )

    async def push_state_to_frontend(self):
        packet = await build_state_packet()

        await self.channel_layer.group_send(
            FRONTEND_GROUP,
            {
                'type': 'send_state',
                'packet': packet,
            },
        )

    async def ws_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': event['event_type'],
                    'data': event['data'],
                }
            )
        )
