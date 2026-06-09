from django.db import migrations, models


def set_existing_default_flow(apps, schema_editor):
    GreenhouseControlProfile = apps.get_model("api", "GreenhouseControlProfile")
    GreenhouseControlProfile.objects.filter(pump_flow_lps=0.02).update(
        pump_flow_lps=0.001
    )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0018_repair_devicecommand_device_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="greenhousecontrolprofile",
            name="pump_flow_lps",
            field=models.FloatField(default=0.001),
        ),
        migrations.RunPython(set_existing_default_flow, migrations.RunPython.noop),
    ]
