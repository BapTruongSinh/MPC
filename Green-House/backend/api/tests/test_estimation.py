from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from api.ampc import default_greenhouse
from api.estimation import ensure_estimation_for_reading, ensure_recent_window_estimations
from api.models import EstimationCycle, SensorData


class LiveEstimationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='estimation', password='pw')
        self.greenhouse = default_greenhouse(user)
        self.start = timezone.now().replace(second=0, microsecond=0)

    def reading(self, offset: int, soil: float, pump: bool = False) -> SensorData:
        return SensorData.objects.create(
            greenhouse=self.greenhouse,
            recorded_at=self.start + timedelta(seconds=offset),
            soil_moisture=soil,
            temperature=28.0,
            humidity=70.0,
            light=5000.0,
            payload={'pump': pump},
        )

    def test_single_reading_is_deduplicated_and_keeps_pump_state(self):
        reading = self.reading(5, 60.0, pump=True)

        first = ensure_estimation_for_reading(reading)
        second = ensure_estimation_for_reading(reading)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.raw_drip, 1.0)
        self.assertEqual(EstimationCycle.objects.count(), 1)

    def test_cycle_index_increments_once_per_new_reading(self):
        first = ensure_estimation_for_reading(self.reading(5, 60.0))
        second = ensure_estimation_for_reading(self.reading(10, 59.0))

        self.assertEqual(second.cycle_index, first.cycle_index + 1)

    def test_recent_windows_create_step_averages(self):
        self.reading(10, 60.0)
        self.reading(40, 54.0)
        self.reading(70, 57.0)

        latest = ensure_recent_window_estimations(
            greenhouse=self.greenhouse,
            step_seconds=60,
            horizon_steps=2,
            end_time=self.start + timedelta(seconds=120),
        )

        self.assertIsNotNone(latest)
        self.assertEqual(latest.source_type, 'live_window')
        self.assertAlmostEqual(latest.raw_soil_moisture, 57.0)

    def test_live_and_window_kalman_streams_do_not_share_cycle_index(self):
        live = ensure_estimation_for_reading(self.reading(5, 60.0))
        self.reading(40, 54.0)
        window = ensure_recent_window_estimations(
            greenhouse=self.greenhouse,
            step_seconds=60,
            horizon_steps=1,
            end_time=self.start + timedelta(seconds=60),
        )
        next_live = ensure_estimation_for_reading(self.reading(65, 53.0))

        self.assertEqual(live.cycle_index, 0)
        self.assertEqual(window.cycle_index, 0)
        self.assertEqual(next_live.cycle_index, 1)
