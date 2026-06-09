from __future__ import annotations

from .models import (
    AMPCSchedulerState,
    ControlState,
    DeviceCommand,
    DeviceState,
    GreenhouseControlProfile,
    SensorData,
)

AUTO_PUMP_SOURCE = 'target_band_auto'
MPC_SCHEDULER_KEY = 'main'


def _control_is_auto() -> bool:
    control = ControlState.objects.get_or_create(singleton_key='main')[0]
    return control.mode == ControlState.Mode.AUTO


def _mpc_is_enabled() -> bool:
    return AMPCSchedulerState.objects.filter(
        singleton_key=MPC_SCHEDULER_KEY,
        is_enabled=True,
    ).exists()


def _profile_for(reading: SensorData) -> GreenhouseControlProfile | None:
    if reading.greenhouse_id is None:
        return GreenhouseControlProfile.objects.filter(singleton_key='main').first()
    return GreenhouseControlProfile.objects.filter(greenhouse=reading.greenhouse).first()


def _pump_is_on() -> bool:
    state = DeviceState.objects.filter(device_code='pump').only('is_on').first()
    return bool(state and state.is_on)


def _queue_pump(value: str, *, soil: float, low: float, stop_at: float, device_code: str) -> DeviceCommand:
    from .services import enqueue_device_command, notify_pending_commands

    cmd = enqueue_device_command(
        device_code='pump',
        command='set_power',
        value=value,
        payload={
            'source': AUTO_PUMP_SOURCE,
            'soil_moisture': round(soil, 3),
            'target_low': round(low, 3),
            'target_stop': round(stop_at, 3),
        },
    )
    if cmd.status == DeviceCommand.CommandStatus.PENDING:
        notify_pending_commands(device_code=device_code)
    return cmd


def run_target_band_auto_pump(reading: SensorData, *, device_code: str = 'esp32-main') -> DeviceCommand | None:
    if reading.soil_moisture is None or not _control_is_auto() or _mpc_is_enabled():
        return None

    profile = _profile_for(reading)
    if profile is None or not profile.actuator_enabled:
        return None

    soil = float(reading.soil_moisture)
    low = float(profile.target_low)
    stop_at = (low + float(profile.target_high)) / 2.0
    pump_on = _pump_is_on()

    if soil <= low and not pump_on:
        return _queue_pump('on', soil=soil, low=low, stop_at=stop_at, device_code=device_code)
    if soil >= stop_at and pump_on:
        return _queue_pump('off', soil=soil, low=low, stop_at=stop_at, device_code=device_code)
    return None
