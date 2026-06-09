from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from mpc.core.types import Recommendation

from api.ampc import default_greenhouse, run_auto_recommendation
from api.et0 import ET0Reading, OpenMeteoError
from api.models import AMPCRecommendation, EstimationCycle


class MpcRuntimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='mpc-runtime', password='pw')
        self.greenhouse = default_greenhouse(self.user)
        self.sample_ts = timezone.now() - timedelta(seconds=5)
        self.estimation = EstimationCycle.objects.create(
            greenhouse=self.greenhouse,
            sample_ts=self.sample_ts,
            cycle_index=1,
            source_type='live_window',
            validation_status='valid',
            preprocess_status=EstimationCycle.PreprocessStatus.VALID,
            cycle_status=EstimationCycle.CycleStatus.OK,
            adaptive_status=EstimationCycle.AdaptiveStatus.R_UPDATED,
            raw_soil_moisture=60.0,
            raw_temperature=28.0,
            raw_humidity=70.0,
            raw_light=5000.0,
            kf_x_posterior=60.0,
            kf_R=1.0,
        )

    def test_successful_run_persists_mpc_audit(self):
        et0 = ET0Reading(
            requested_hour=self.sample_ts.replace(minute=0, second=0, microsecond=0),
            et0_hour_mm=0.6,
            et0_step_mm=0.05,
            step_seconds=300,
        )
        recommendation = Recommendation(
            pump_seconds=0.0,
            step_seconds=300,
            predicted_soil_moisture=(59.9,),
            target_band={'low': 55.0, 'high': 65.0},
            cost=1.0,
            safety_status='safe',
            reason='within_raw',
            fao56={'initial_dr': 10.0},
        )

        with (
            patch('api.ampc.ensure_recent_window_estimations', return_value=self.estimation),
            patch('api.ampc.get_hourly_et0', return_value=et0),
            patch('api.ampc.ScipyMpcSolver') as solver,
        ):
            solver.return_value.recommend.return_value = recommendation
            audit = run_auto_recommendation(user=self.user, create_command_if_auto=False)

        self.assertEqual(audit.safety_status, 'safe')
        self.assertEqual(audit.predicted_soil_moisture, [59.9])
        self.assertEqual(audit.state_snapshot['et0']['et0_step_mm'], 0.05)
        self.assertEqual(audit.state_snapshot['fao56']['initial_dr'], 10.0)

    def test_et0_failure_stops_before_solver_and_does_not_queue_pump(self):
        with (
            patch('api.ampc.ensure_recent_window_estimations', return_value=self.estimation),
            patch('api.ampc.get_hourly_et0', side_effect=OpenMeteoError('timeout')),
            patch('api.ampc.ScipyMpcSolver') as solver,
        ):
            audit = run_auto_recommendation(user=self.user)

        solver.assert_not_called()
        self.assertEqual(audit.safety_status, 'model_error')
        self.assertEqual(audit.pump_seconds, 0.0)
        self.assertFalse(audit.command_created)
        self.assertEqual(AMPCRecommendation.objects.count(), 1)
