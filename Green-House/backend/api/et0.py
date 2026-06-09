from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone as datetime_timezone
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from .user_resources import default_owner, ensure_user_control_profile

OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'
ET0_VARIABLE = 'et0_fao_evapotranspiration'
DEFAULT_TIMEOUT_SECONDS = 5.0


class OpenMeteoError(Exception):
    pass


@dataclass(frozen=True)
class ET0Reading:
    requested_hour: datetime
    et0_hour_mm: float
    et0_step_mm: float
    step_seconds: int


def get_hourly_et0(
    when: datetime,
    *,
    step_seconds: int,
    owner=None,
) -> ET0Reading:
    requested_hour = _utc(when).replace(minute=0, second=0, microsecond=0)
    latitude, longitude = _coordinates(owner)
    step_seconds = _positive_int(step_seconds)
    et0_hour_mm = _extract_et0(
        _fetch_open_meteo(latitude, longitude, requested_hour),
        requested_hour,
    )
    return ET0Reading(
        requested_hour=requested_hour,
        et0_hour_mm=et0_hour_mm,
        et0_step_mm=et0_hour_mm * step_seconds / 3600,
        step_seconds=step_seconds,
    )


def _fetch_open_meteo(latitude: float, longitude: float, hour: datetime) -> dict[str, Any]:
    timeout = _number(getattr(settings, 'OPEN_METEO_ET0_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS))
    if timeout <= 0:
        raise OpenMeteoError('timeout_invalid')
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': ET0_VARIABLE,
        'timezone': 'UTC',
        'start_date': hour.date().isoformat(),
        'end_date': hour.date().isoformat(),
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise OpenMeteoError(exc.__class__.__name__) from exc
    except ValueError as exc:
        raise OpenMeteoError('invalid_json') from exc
    if not isinstance(payload, dict):
        raise OpenMeteoError('invalid_payload')
    return payload


def _extract_et0(payload: dict[str, Any], requested_hour: datetime) -> float:
    hourly = payload.get('hourly')
    times = hourly.get('time') if isinstance(hourly, dict) else None
    values = hourly.get(ET0_VARIABLE) if isinstance(hourly, dict) else None
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        raise OpenMeteoError('invalid_hourly_et0')

    wanted = requested_hour.strftime('%Y-%m-%dT%H:%M')
    for timestamp, value in zip(times, values):
        if timestamp in {wanted, f'{wanted}:00'}:
            et0 = _number(value)
            if et0 < 0:
                raise OpenMeteoError('et0_negative')
            return et0
    raise OpenMeteoError('requested_hour_not_found')


def _coordinates(owner) -> tuple[float, float]:
    profile = ensure_user_control_profile(owner or default_owner())
    latitude, longitude = _number(profile.latitude), _number(profile.longitude)
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise OpenMeteoError('coordinates_out_of_range')
    return latitude, longitude


def _number(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise OpenMeteoError('number_invalid') from exc
    if not math.isfinite(result):
        raise OpenMeteoError('number_not_finite')
    return result


def _positive_int(value: Any) -> int:
    try:
        result = int(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise OpenMeteoError('step_seconds_invalid') from exc
    if result <= 0:
        raise OpenMeteoError('step_seconds_invalid')
    return result


def _utc(value: datetime) -> datetime:
    if timezone.is_naive(value):
        value = timezone.make_aware(value, datetime_timezone.utc)
    return value.astimezone(datetime_timezone.utc)
