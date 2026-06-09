from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.ampc import default_greenhouse, get_greenhouse_control_profile
from api.estimation import ensure_estimation_for_sensor_window
from api.models import AMPCRecommendation, EstimationCycle, Greenhouse, GreenhouseControlProfile, SensorData
from api.services import ingest_sensor_payload


class GreenHouseRuntimeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST='127.0.0.1')
        self.user = User.objects.create_user(username='tester', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_auto_settings_uses_current_ampc_schema(self):
        response = self.client.get('/api/auto-settings/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('theta_fc', payload)
        self.assertIn('theta_wp', payload)
        self.assertNotIn('theta_sat', payload)
        self.assertNotIn('pump_grid_seconds', payload)
        self.assertNotIn('adaptive_enabled', payload)
        self.assertNotIn('adaptive_rls_window', payload)
        self.assertNotIn('adaptive_max_abs_residual', payload)
        self.assertNotIn('adaptive_bias_window', payload)
        self.assertNotIn('adaptive_max_abs_bias', payload)
        self.assertNotIn('soft_daily_pump_cap_seconds', payload)
        self.assertNotIn('weight_daily', payload)

    def test_auto_settings_soil_preset_updates_theta_without_theta_sat(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {
                'soil_type': 'light_loam',
                'root_depth_m': 0.35,
                'step_seconds': 120,
                'horizon_steps': 10,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['soil_type'], 'light_loam')
        self.assertEqual(payload['theta_fc'], 0.15)
        self.assertEqual(payload['theta_wp'], 0.06)
        self.assertEqual(payload['root_depth_m'], 0.35)
        self.assertEqual(payload['step_seconds'], 120)
        self.assertEqual(payload['pump_max_seconds'], 120)
        self.assertEqual(payload['horizon_steps'], 10)
        self.assertNotIn('theta_sat', payload)

    def test_auto_settings_rejects_direct_theta_inputs(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {
                'theta_wp': 0.36,
                'theta_fc': 0.32,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('theta_fc', response.json())
        self.assertIn('theta_wp', response.json())
        profile = get_greenhouse_control_profile(self.user)
        self.assertEqual(profile.theta_wp, 0.15)
        self.assertEqual(profile.theta_fc, 0.32)

    def test_auto_settings_rejects_direct_pump_max_seconds(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {'pump_max_seconds': 60},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('pump_max_seconds', response.json())

    def test_auto_settings_rejects_step_not_aligned_to_esp32_sampling(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {'step_seconds': 121},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('step_seconds', response.json())

    def test_threshold_settings_returns_defaults(self):
        response = self.client.get('/api/settings/thresholds/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['thresh_temp_fan_on'], 32.0)
        self.assertEqual(payload['thresh_soil_pump_on'], 35.0)

    def test_threshold_settings_updates_current_user_greenhouse(self):
        response = self.client.patch(
            '/api/settings/thresholds/',
            {'thresh_soil_pump_on': 38.0, 'thresh_soil_pump_off': 42.0},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        profile = get_greenhouse_control_profile(self.user)
        self.assertEqual(profile.thresh_soil_pump_on, 38.0)
        self.assertEqual(profile.thresh_soil_pump_off, 42.0)

        other = User.objects.create_user(username='threshold-other', password='pw')
        other_profile = get_greenhouse_control_profile(other)
        self.assertEqual(other_profile.thresh_soil_pump_on, 35.0)
        self.assertEqual(other_profile.thresh_soil_pump_off, 40.0)

    def test_threshold_settings_rejects_invalid_hysteresis(self):
        response = self.client.patch(
            '/api/settings/thresholds/',
            {'thresh_soil_pump_on': 45.0, 'thresh_soil_pump_off': 40.0},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('thresh_soil_pump_off', response.json())

    def test_ingest_payload_persists_esp32_device_snapshot(self):
        reading = ingest_sensor_payload({
            'soil_moisture': 55.0,
            'temperature': 30.0,
            'humidity': 70.0,
            'light': 400.0,
            'pump': True,
            'fan': False,
            'mist': True,
            'mode': 'auto',
            'auto_mode': True,
            'payload': {'sun_tracker': {'servo_vertical': 45}},
            'device_states': {'pump_on': True, 'fan_on': False, 'mist_on': True},
            'sensor_errors': {'dht': False, 'soil': False},
        })

        self.assertTrue(reading.payload['pump'])
        self.assertFalse(reading.payload['fan'])
        self.assertTrue(reading.payload['mist'])
        self.assertEqual(reading.payload['device_states']['pump_on'], True)
        self.assertEqual(reading.payload['sun_tracker']['servo_vertical'], 45)

    def test_ingest_payload_respects_greenhouse_id_and_overwrites_timestamp(self):
        greenhouse = default_greenhouse(self.user)
        sample_ts = timezone.now().replace(microsecond=0)
        stale_reading = SensorData.objects.create(
            greenhouse=greenhouse,
            recorded_at=sample_ts,
            soil_moisture=40.0,
            temperature=27.0,
            humidity=65.0,
            light=3000.0,
        )
        stale_cycle = EstimationCycle.objects.create(
            greenhouse=greenhouse,
            sample_ts=sample_ts,
            cycle_index=999,
            source_type='live',
            validation_status='valid',
            preprocess_status=EstimationCycle.PreprocessStatus.VALID,
            cycle_status=EstimationCycle.CycleStatus.OK,
            adaptive_status=EstimationCycle.AdaptiveStatus.R_UPDATED,
            raw_soil_moisture=40.0,
            raw_temperature=27.0,
            raw_humidity=65.0,
            raw_light=3000.0,
            kf_x_posterior=40.0,
            kf_R=1.0,
        )
        stale_window = EstimationCycle.objects.create(
            greenhouse=greenhouse,
            sample_ts=sample_ts + timedelta(minutes=5),
            cycle_index=1000,
            source_type='live_window',
            validation_status='valid',
            preprocess_status=EstimationCycle.PreprocessStatus.VALID,
            cycle_status=EstimationCycle.CycleStatus.OK,
            adaptive_status=EstimationCycle.AdaptiveStatus.R_UPDATED,
            raw_soil_moisture=40.0,
            raw_temperature=27.0,
            raw_humidity=65.0,
            raw_light=3000.0,
            kf_x_posterior=40.0,
            kf_R=1.0,
        )

        reading = ingest_sensor_payload({
            'greenhouse_id': greenhouse.id,
            'overwrite': True,
            'recorded_at': sample_ts.isoformat(),
            'soil_moisture': 55.0,
            'temperature': 28.0,
            'humidity': 70.0,
            'light': 5500.0,
            'device_states': {'pump_on': False},
            'sensor_errors': {},
            'payload': {'source': 'test-replay'},
        })

        self.assertEqual(reading.greenhouse_id, greenhouse.id)
        self.assertFalse(SensorData.objects.filter(pk=stale_reading.pk).exists())
        self.assertFalse(EstimationCycle.objects.filter(pk=stale_cycle.pk).exists())
        self.assertFalse(EstimationCycle.objects.filter(pk=stale_window.pk).exists())
        stored_values = list(
            SensorData.objects
            .filter(greenhouse=greenhouse, recorded_at=sample_ts)
            .values_list('soil_moisture', flat=True)
        )
        self.assertEqual(len(stored_values), 1)
        self.assertAlmostEqual(float(stored_values[0]), 55.0)

    def test_window_estimation_averages_raw_sensor_data(self):
        greenhouse = default_greenhouse(self.user)
        start = timezone.now().replace(microsecond=0)
        rows = [
            (30, 60.0, True),
            (60, 54.0, False),
            (90, 57.0, True),
        ]
        for offset, soil, pump_on in rows:
            SensorData.objects.create(
                greenhouse=greenhouse,
                recorded_at=start + timedelta(seconds=offset),
                soil_moisture=soil,
                temperature=30.0 + offset / 30,
                humidity=70.0,
                light=400.0,
                payload={'pump': pump_on, 'device_states': {'pump_on': pump_on}},
            )

        cycle = ensure_estimation_for_sensor_window(
            greenhouse=greenhouse,
            window_start=start,
            window_end=start + timedelta(seconds=120),
            step_seconds=120,
        )

        self.assertIsNotNone(cycle)
        assert cycle is not None
        self.assertEqual(cycle.source_type, 'live_window')
        self.assertAlmostEqual(cycle.raw_soil_moisture, 57.0)
        self.assertAlmostEqual(cycle.raw_drip, 2 / 3)

    def test_forecast_history_normalizes_live_window_cycles(self):
        greenhouse = default_greenhouse(self.user)
        start = timezone.now().replace(microsecond=0)
        for index, soil in enumerate([61.0, 58.0]):
            cycle = EstimationCycle.objects.create(
                greenhouse=greenhouse,
                sample_ts=start + timedelta(minutes=5 * index),
                cycle_index=index,
                source_type='live_window',
                validation_status='valid',
                preprocess_status=EstimationCycle.PreprocessStatus.VALID,
                cycle_status=EstimationCycle.CycleStatus.OK,
                adaptive_status=EstimationCycle.AdaptiveStatus.R_UPDATED,
                raw_soil_moisture=soil,
                raw_temperature=28.0,
                raw_humidity=70.0,
                raw_light=5500.0,
                kf_x_posterior=soil,
                kf_R=1.0,
            )

        AMPCRecommendation.objects.create(
            greenhouse=greenhouse,
            estimation=cycle,
            pump_seconds=0.0,
            step_seconds=300,
            predicted_soil_moisture=[58.0],
            target_band={'low': 55.0, 'high': 65.0},
            objective_cost=0.0,
            safety_status='safe',
            reason='within_raw',
        )

        response = self.client.get('/api/forecast/')

        self.assertEqual(response.status_code, 200)
        history = response.json()['history']
        self.assertEqual([row['soil_moisture'] for row in history], [61.0, 58.0])
        self.assertIn('recorded_at', history[0])
        self.assertNotIn('sample_ts', history[0])

    def test_forecast_history_prefers_step_sampled_sensor_rows(self):
        greenhouse = default_greenhouse(self.user)
        start = timezone.now().replace(microsecond=0)
        for index, soil in enumerate([70.0, 68.0, 66.0, 64.0, 62.0, 60.0]):
            SensorData.objects.create(
                greenhouse=greenhouse,
                recorded_at=start + timedelta(minutes=5 * index),
                soil_moisture=soil,
                temperature=28.0,
                humidity=70.0,
                light=5500.0,
                payload={'source': 'test-replay'},
            )

        stale_window = EstimationCycle.objects.create(
            greenhouse=greenhouse,
            sample_ts=start + timedelta(minutes=25),
            cycle_index=1,
            source_type='live_window',
            validation_status='valid',
            preprocess_status=EstimationCycle.PreprocessStatus.VALID,
            cycle_status=EstimationCycle.CycleStatus.OK,
            adaptive_status=EstimationCycle.AdaptiveStatus.R_UPDATED,
            raw_soil_moisture=55.0,
            raw_temperature=28.0,
            raw_humidity=70.0,
            raw_light=5500.0,
            kf_x_posterior=55.0,
            kf_R=1.0,
        )

        AMPCRecommendation.objects.create(
            greenhouse=greenhouse,
            estimation=stale_window,
            pump_seconds=0.0,
            step_seconds=300,
            predicted_soil_moisture=[60.0],
            target_band={'low': 55.0, 'high': 65.0},
            objective_cost=0.0,
            safety_status='safe',
            reason='within_raw',
        )

        response = self.client.get('/api/forecast/')

        self.assertEqual(response.status_code, 200)
        history = response.json()['history']
        self.assertEqual([row['soil_moisture'] for row in history], [70.0, 68.0, 66.0, 64.0, 62.0, 60.0])
        self.assertEqual(history[0]['payload']['source'], 'test-replay')

    def test_forecast_recommendation_has_no_legacy_adaptive_fields(self):
        greenhouse = default_greenhouse(self.user)
        AMPCRecommendation.objects.create(
            greenhouse=greenhouse,
            pump_seconds=0.0,
            step_seconds=300,
            predicted_soil_moisture=[60.0],
            target_band={'low': 55.0, 'high': 65.0},
            objective_cost=0.0,
            safety_status='safe',
            reason='within_raw',
        )

        response = self.client.get('/api/forecast/')

        self.assertEqual(response.status_code, 200)
        recommendation = response.json()['recommendation']
        self.assertNotIn('rls_update_count', recommendation)
        self.assertNotIn('rls_skipped_count', recommendation)
        self.assertNotIn('bias_correction', recommendation)
        self.assertNotIn('bias_window_count', recommendation)

    def test_auto_settings_are_scoped_to_authenticated_user_greenhouse(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {'target_low': 50.0, 'target_high': 62.0},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        other = User.objects.create_user(username='other', password='pw')
        self.client.force_authenticate(user=other)
        response = self.client.get('/api/auto-settings/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['target_low'], 55.0)
        self.assertEqual(payload['target_high'], 65.0)
        first_profile = get_greenhouse_control_profile(self.user)
        second_profile = get_greenhouse_control_profile(other)
        self.assertNotEqual(first_profile.greenhouse_id, second_profile.greenhouse_id)
        self.assertEqual(first_profile.target_low, 50.0)
        self.assertEqual(second_profile.target_low, 55.0)

    def test_new_user_creation_seeds_default_greenhouse_and_config(self):
        user = User.objects.create_user(username='new-user', password='pw')

        greenhouse = Greenhouse.objects.get(owner=user, name='Main greenhouse')
        profile = GreenhouseControlProfile.objects.get(greenhouse=greenhouse)
        self.assertEqual(profile.target_low, 55.0)
        self.assertEqual(profile.target_high, 65.0)

    def _cycle(self, *, greenhouse, sample_ts, cycle_index, source_type, soil):
        return EstimationCycle.objects.create(
            greenhouse=greenhouse,
            sample_ts=sample_ts,
            cycle_index=cycle_index,
            source_type=source_type,
            validation_status='valid',
            preprocess_status=EstimationCycle.PreprocessStatus.VALID,
            cycle_status=EstimationCycle.CycleStatus.OK,
            adaptive_status=EstimationCycle.AdaptiveStatus.R_UPDATED,
            raw_soil_moisture=soil,
            raw_temperature=30.0,
            raw_humidity=70.0,
            raw_light=400.0,
            kf_x_posterior=soil,
            kf_R=1.0,
        )
