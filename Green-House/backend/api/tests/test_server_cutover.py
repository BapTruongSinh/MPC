from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.ampc import get_control_profile
from api.estimation import ensure_estimation_for_sensor_window
from api.models import (
    AMPCRecommendation,
    AMPCSchedulerState,
    ControlState,
    DeviceCommand,
    DeviceState,
    EstimationCycle,
    GreenhouseControlProfile,
    SensorData,
)
from api.services import enqueue_device_command, ingest_sensor_payload


class OwnerScopedRuntimeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST='127.0.0.1')
        self.admin = User.objects.create_superuser(username='admin', password='pw', email='')
        self.user = User.objects.create_user(username='tester', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_auto_settings_uses_current_mpc_schema(self):
        response = self.client.get('/api/auto-settings/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('theta_fc', payload)
        self.assertIn('theta_wp', payload)
        self.assertNotIn('theta_sat', payload)
        self.assertNotIn('pump_grid_seconds', payload)
        self.assertNotIn('soft_daily_pump_cap_seconds', payload)
        self.assertNotIn('weight_daily', payload)

    def test_auto_settings_soil_preset_updates_derived_theta(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {'soil_type': 'light_loam', 'root_depth_m': 0.35, 'step_seconds': 120},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['soil_type'], 'light_loam')
        self.assertEqual(payload['theta_fc'], 0.15)
        self.assertEqual(payload['theta_wp'], 0.06)
        self.assertEqual(payload['pump_max_seconds'], 120)

    def test_auto_settings_rejects_direct_derived_inputs(self):
        response = self.client.patch(
            '/api/auto-settings/',
            {'theta_wp': 0.36, 'theta_fc': 0.32, 'pump_max_seconds': 60},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn('theta_fc', payload)
        self.assertIn('theta_wp', payload)
        self.assertIn('pump_max_seconds', payload)

    def test_threshold_settings_are_scoped_to_user_owner(self):
        response = self.client.patch(
            '/api/settings/thresholds/',
            {'thresh_soil_pump_on': 38.0, 'thresh_soil_pump_off': 42.0},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_control_profile(self.user).thresh_soil_pump_on, 38.0)

        other = User.objects.create_user(username='other', password='pw')
        self.assertEqual(get_control_profile(other).thresh_soil_pump_on, 35.0)

    def test_ingest_defaults_to_admin_owner_and_accepts_owner_id(self):
        admin_reading = ingest_sensor_payload({
            'soil_moisture': 55.0,
            'temperature': 30.0,
            'humidity': 70.0,
            'light': 400.0,
            'device_states': {'pump_on': False},
        })
        user_reading = ingest_sensor_payload({
            'owner_id': self.user.id,
            'soil_moisture': 56.0,
            'temperature': 30.0,
            'humidity': 70.0,
            'light': 400.0,
            'device_states': {'pump_on': False},
        })

        self.assertEqual(admin_reading.owner_id, self.admin.id)
        self.assertEqual(user_reading.owner_id, self.user.id)

    def test_ingest_overwrite_replaces_sensor_and_estimation_rows_for_owner(self):
        sample_ts = timezone.now().replace(microsecond=0)
        stale_reading = SensorData.objects.create(
            owner=self.user,
            recorded_at=sample_ts,
            soil_moisture=40.0,
            temperature=27.0,
            humidity=65.0,
            light=3000.0,
        )
        stale_cycle = self._cycle(sample_ts=sample_ts, cycle_index=1, source_type='live', soil=40.0)
        stale_window = self._cycle(
            sample_ts=sample_ts + timedelta(minutes=5),
            cycle_index=2,
            source_type='live_window',
            soil=40.0,
        )

        reading = ingest_sensor_payload({
            'owner_id': self.user.id,
            'overwrite': True,
            'recorded_at': sample_ts.isoformat(),
            'soil_moisture': 55.0,
            'temperature': 28.0,
            'humidity': 70.0,
            'light': 5500.0,
            'device_states': {'pump_on': False},
        })

        self.assertEqual(reading.owner_id, self.user.id)
        self.assertFalse(SensorData.objects.filter(pk=stale_reading.pk).exists())
        self.assertFalse(EstimationCycle.objects.filter(pk=stale_cycle.pk).exists())
        self.assertFalse(EstimationCycle.objects.filter(pk=stale_window.pk).exists())
        stored = SensorData.objects.get(owner=self.user, recorded_at=sample_ts)
        self.assertAlmostEqual(float(stored.soil_moisture), 55.0)

    def test_window_estimation_averages_owner_sensor_data(self):
        start = timezone.now().replace(microsecond=0)
        for offset, soil, pump_on in [(30, 60.0, True), (60, 54.0, False), (90, 57.0, True)]:
            SensorData.objects.create(
                owner=self.user,
                recorded_at=start + timedelta(seconds=offset),
                soil_moisture=soil,
                temperature=30.0,
                humidity=70.0,
                light=400.0,
                payload={'device_states': {'pump_on': pump_on}},
            )

        cycle = ensure_estimation_for_sensor_window(
            owner=self.user,
            window_start=start,
            window_end=start + timedelta(seconds=120),
            step_seconds=120,
        )

        self.assertIsNotNone(cycle)
        self.assertEqual(cycle.source_type, 'live_window')
        self.assertAlmostEqual(cycle.raw_soil_moisture, 57.0)
        self.assertAlmostEqual(cycle.raw_drip, 2 / 3)

    def test_forecast_history_prefers_step_sampled_owner_sensor_rows(self):
        start = timezone.now().replace(microsecond=0)
        for index, soil in enumerate([70.0, 68.0, 66.0, 64.0, 62.0, 60.0]):
            SensorData.objects.create(
                owner=self.user,
                recorded_at=start + timedelta(minutes=5 * index),
                soil_moisture=soil,
                temperature=28.0,
                humidity=70.0,
                light=5500.0,
                payload={'source': 'test-replay'},
            )
        estimation = self._cycle(
            sample_ts=start + timedelta(minutes=25),
            cycle_index=1,
            source_type='live_window',
            soil=60.0,
        )
        AMPCRecommendation.objects.create(
            owner=self.user,
            estimation=estimation,
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

    def test_auto_target_band_controls_pump_only_when_mpc_is_off(self):
        control, _ = ControlState.objects.get_or_create(singleton_key='main')
        control.mode = ControlState.Mode.AUTO
        control.save(update_fields=['mode', 'updated_at'])

        profile = get_control_profile(self.user)
        profile.actuator_enabled = True
        profile.target_low = 55.0
        profile.target_high = 65.0
        profile.save(update_fields=['actuator_enabled', 'target_low', 'target_high', 'updated_at'])

        ingest_sensor_payload({
            'owner_id': self.user.id,
            'soil_moisture': 54.0,
            'temperature': 29.0,
            'humidity': 70.0,
            'light': 5500.0,
            'mode': 'auto',
            'device_states': {'pump_on': False},
        })
        cmd = DeviceCommand.objects.get(device_code='pump')
        self.assertEqual(cmd.value, 'on')
        self.assertEqual(cmd.payload['source'], 'target_band_auto')

        DeviceCommand.objects.all().delete()
        AMPCSchedulerState.objects.update_or_create(
            singleton_key='main',
            defaults={'is_enabled': True, 'interval_seconds': 300},
        )
        ingest_sensor_payload({
            'owner_id': self.user.id,
            'soil_moisture': 54.0,
            'temperature': 29.0,
            'humidity': 70.0,
            'light': 5500.0,
            'mode': 'auto',
            'device_states': {'pump_on': False},
        })
        self.assertFalse(DeviceCommand.objects.filter(device_code='pump').exists())

    def test_mpc_pump_on_command_is_skipped_when_pump_is_running(self):
        DeviceState.objects.create(device_code='pump', is_on=True, desired_on=True)

        cmd = enqueue_device_command(
            device_code='pump',
            command='set_power',
            value='on',
            payload={'source': 'mpc', 'duration': 30},
        )

        self.assertEqual(cmd.status, DeviceCommand.CommandStatus.SKIPPED)
        self.assertEqual(cmd.payload['skip_reason'], 'pump_already_on')

    def test_new_user_creation_seeds_default_control_profile(self):
        user = User.objects.create_user(username='new-user', password='pw')

        profile = GreenhouseControlProfile.objects.get(owner=user)
        self.assertEqual(profile.target_low, 55.0)
        self.assertEqual(profile.target_high, 65.0)

    def _cycle(self, *, sample_ts, cycle_index, source_type, soil):
        return EstimationCycle.objects.create(
            owner=self.user,
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
