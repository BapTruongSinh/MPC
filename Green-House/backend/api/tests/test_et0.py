from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.test import TestCase

from api.et0 import ET0Reading, OpenMeteoError, get_hourly_et0
from api.models import GreenhouseControlProfile


class OpenMeteoET0ServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='et0', password='pw')
        GreenhouseControlProfile.objects.update_or_create(
            owner=self.owner,
            defaults={'latitude': 16.0471, 'longitude': 108.2068},
        )
        self.when = datetime(2026, 5, 12, 9, 23, tzinfo=timezone.utc)

    @staticmethod
    def response(et0=0.72):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'hourly': {
                'time': ['2026-05-12T09:00'],
                'et0_fao_evapotranspiration': [et0],
            },
        }
        return response

    @patch('api.et0.requests.get')
    def test_returns_hourly_and_step_et0(self, get):
        get.return_value = self.response()

        result = get_hourly_et0(self.when, step_seconds=900, owner=self.owner)

        self.assertIsInstance(result, ET0Reading)
        self.assertEqual(result.requested_hour, datetime(2026, 5, 12, 9, tzinfo=timezone.utc))
        self.assertAlmostEqual(result.et0_hour_mm, 0.72)
        self.assertAlmostEqual(result.et0_step_mm, 0.18)
        get.assert_called_once()

    @patch('api.et0.requests.get')
    def test_each_call_fetches_open_meteo_once(self, get):
        get.return_value = self.response()

        get_hourly_et0(self.when, step_seconds=300, owner=self.owner)
        get_hourly_et0(self.when, step_seconds=300, owner=self.owner)

        self.assertEqual(get.call_count, 2)

    @patch('api.et0.requests.get')
    def test_network_failure_raises_open_meteo_error(self, get):
        get.side_effect = requests.Timeout()

        with self.assertRaises(OpenMeteoError):
            get_hourly_et0(self.when, step_seconds=300, owner=self.owner)

    @patch('api.et0.requests.get')
    def test_invalid_et0_raises_open_meteo_error(self, get):
        get.return_value = self.response(float('inf'))

        with self.assertRaises(OpenMeteoError):
            get_hourly_et0(self.when, step_seconds=300, owner=self.owner)
