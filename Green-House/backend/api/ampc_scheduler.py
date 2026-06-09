from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import timedelta

from django.db import OperationalError, ProgrammingError, close_old_connections, transaction
from django.utils import timezone

from .ampc import run_auto_recommendation
from .models import AMPCSchedulerState, GreenhouseControlProfile
from .user_resources import default_owner, ensure_user_control_profile

logger = logging.getLogger(__name__)

SCHEDULER_KEY = 'main'
DEFAULT_INTERVAL_SECONDS = 300
POLL_SECONDS = 5
STALE_EXECUTION_FACTOR = 2

_thread_started = False
_thread_lock = threading.Lock()


def get_scheduler_state() -> AMPCSchedulerState:
    return AMPCSchedulerState.objects.get_or_create(
        singleton_key=SCHEDULER_KEY,
        defaults={'interval_seconds': DEFAULT_INTERVAL_SECONDS, 'is_enabled': False},
    )[0]


def _active_interval_seconds() -> int:
    step_seconds = (
        GreenhouseControlProfile.objects
        .exclude(owner__isnull=True)
        .order_by('step_seconds')
        .values_list('step_seconds', flat=True)
        .first()
    )
    return int(step_seconds or DEFAULT_INTERVAL_SECONDS)


def _save_state(state: AMPCSchedulerState, **values) -> AMPCSchedulerState:
    for field, value in values.items():
        setattr(state, field, value)
    state.save(update_fields=[*values, 'updated_at'])
    return state


def start_scheduler() -> AMPCSchedulerState:
    return _save_state(
        get_scheduler_state(),
        is_enabled=True,
        is_executing=False,
        interval_seconds=_active_interval_seconds(),
        last_started_at=timezone.now(),
        next_run_at=timezone.now(),
        last_error='',
    )


def stop_scheduler() -> AMPCSchedulerState:
    return _save_state(
        get_scheduler_state(),
        is_enabled=False,
        is_executing=False,
        last_stopped_at=timezone.now(),
        next_run_at=None,
    )


def _execution_is_stale(state: AMPCSchedulerState, now) -> bool:
    interval = max(state.interval_seconds or DEFAULT_INTERVAL_SECONDS, 1)
    return state.updated_at <= now - timedelta(seconds=interval * STALE_EXECUTION_FACTOR)


def _should_run(state: AMPCSchedulerState, now, *, force: bool) -> bool:
    executing = state.is_executing and not _execution_is_stale(state, now)
    due = force or not state.next_run_at or state.next_run_at <= now
    return state.is_enabled and not executing and due


def _state_filter(state_id: int | None) -> dict:
    return {'pk': state_id} if state_id is not None else {'singleton_key': SCHEDULER_KEY}


def _run_recommendations() -> tuple[str, str]:
    owners = list(
        GreenhouseControlProfile.objects
        .exclude(owner__isnull=True)
        .select_related('owner')
        .order_by('owner_id')
    )
    if not owners:
        owner = default_owner()
        ensure_user_control_profile(owner)
        owners = [ensure_user_control_profile(owner)]
    recommendations = [
        run_auto_recommendation(create_command_if_auto=True, owner=profile.owner)
        for profile in owners
    ]
    unsafe = [item for item in recommendations if item.safety_status != 'safe']
    if not unsafe:
        return f'{len(recommendations)} owner safe', ''
    error = '; '.join((item.reason or item.safety_status)[:120] for item in unsafe[:3])
    return f'{len(unsafe)}/{len(recommendations)} unsafe', error


def _finish_run(state: AMPCSchedulerState, *, status: str, error: str) -> AMPCSchedulerState:
    finished_at = timezone.now()
    interval = max(_active_interval_seconds(), 1)
    AMPCSchedulerState.objects.filter(pk=state.pk).update(
        interval_seconds=interval,
        is_executing=False,
        last_run_at=finished_at,
        next_run_at=finished_at + timedelta(seconds=interval),
        last_status=status,
        last_error=error,
        updated_at=finished_at,
    )
    return AMPCSchedulerState.objects.get(pk=state.pk)


def run_due_once(*, force: bool = False, state_id: int | None = None) -> AMPCSchedulerState | None:
    try:
        state = AMPCSchedulerState.objects.get(**_state_filter(state_id))
    except AMPCSchedulerState.DoesNotExist:
        return None

    now = timezone.now()
    if not _should_run(state, now, force=force):
        return state

    with transaction.atomic():
        state = AMPCSchedulerState.objects.select_for_update().get(pk=state.pk)
        if not _should_run(state, now, force=force):
            return state
        _save_state(state, is_executing=True)

    try:
        status, error = _run_recommendations()
    except Exception as exc:  # pragma: no cover
        logger.exception('MPC scheduler run failed')
        status, error = 'error', str(exc)
    return _finish_run(state, status=status, error=error)


def _should_start_background_thread() -> bool:
    command = ' '.join(sys.argv)
    if sys.argv and sys.argv[0].endswith('manage.py') and 'runserver' not in command:
        return False
    return 'runserver' not in command or os.environ.get('RUN_MAIN') == 'true'


def _scheduler_loop() -> None:
    while True:
        try:
            close_old_connections()
            run_due_once()
        except (OperationalError, ProgrammingError):
            logger.debug('MPC scheduler skipped because database is not ready', exc_info=True)
        except Exception:
            logger.exception('MPC scheduler loop failed')
        finally:
            close_old_connections()
            time.sleep(POLL_SECONDS)


def start_background_scheduler() -> None:
    global _thread_started

    if not _should_start_background_thread():
        return

    with _thread_lock:
        if not _thread_started:
            threading.Thread(target=_scheduler_loop, name='mpc-scheduler', daemon=True).start()
            _thread_started = True
