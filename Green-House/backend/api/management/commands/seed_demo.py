from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.ampc import default_control_owner
from api.models import Alert, DeviceCommand, DeviceState, SensorData


class Command(BaseCommand):
    help = 'Seed device state and demo sensor data for the current day.'

    def handle(self, *args, **options):
        now_local = timezone.localtime()
        today = now_local.date()
        tz = timezone.get_current_timezone()
        owner = default_control_owner()

        for device_code, is_on in [
            ('esp32-main', True),
            ('fan', False),
            ('pump', False),
            ('light', False),
            ('mist', False),
        ]:
            DeviceState.objects.update_or_create(
                device_code=device_code,
                defaults={
                    'is_on': is_on,
                    'desired_on': is_on,
                    'last_command': '',
                    'last_value': 'on' if is_on else 'off',
                    'extra': {},
                },
            )

        Alert.objects.all().delete()
        DeviceCommand.objects.all().delete()
        SensorData.objects.filter(owner=owner).delete()

        samples = [
            ('08:10', Decimal('27.8'), Decimal('74.0'), Decimal('32.0'), Decimal('48.0'), 180),
            ('09:00', Decimal('28.4'), Decimal('72.5'), Decimal('38.0'), Decimal('46.5'), 220),
            ('09:50', Decimal('29.1'), Decimal('70.8'), Decimal('44.0'), Decimal('44.0'), 260),
            ('10:40', Decimal('30.0'), Decimal('68.0'), Decimal('55.0'), Decimal('41.5'), 320),
            ('11:30', Decimal('31.0'), Decimal('65.5'), Decimal('67.0'), Decimal('39.0'), 410),
            ('12:20', Decimal('31.8'), Decimal('62.0'), Decimal('78.0'), Decimal('36.5'), 520),
            ('13:10', Decimal('32.2'), Decimal('60.0'), Decimal('83.0'), Decimal('34.0'), 610),
            ('14:00', Decimal('31.6'), Decimal('61.8'), Decimal('76.0'), Decimal('33.0'), 560),
            ('14:50', Decimal('30.9'), Decimal('63.5'), Decimal('69.0'), Decimal('31.5'), 470),
        ]

        created = []
        for hhmm, temp, hum, light_pct, soil, mq135_ppm in samples:
            hour, minute = map(int, hhmm.split(':'))
            recorded_at = timezone.make_aware(datetime.combine(today, time(hour, minute)), tz)

            created.append(
                SensorData.objects.create(
                    owner=owner,
                    temperature=temp,
                    humidity=hum,
                    light=light_pct,
                    soil_moisture=soil,
                    payload={
                        'source': 'seed_demo',
                        'mq135_ppm': mq135_ppm,
                    },
                    recorded_at=recorded_at,
                    received_at=recorded_at,
                )
            )

        latest = created[-1]
        DeviceState.objects.filter(device_code='esp32-main').update(
            extra={'last_seen_at': latest.recorded_at.isoformat()},
            updated_at=timezone.now(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {len(created)} readings for {today.isoformat()}; latest at 14:50.'
            )
        )
