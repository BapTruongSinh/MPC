from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_seed_user_greenhouse_configs'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='controlprofile',
            name='adaptive_enabled',
        ),
        migrations.RemoveField(
            model_name='controlprofile',
            name='adaptive_rls_window',
        ),
        migrations.RemoveField(
            model_name='controlprofile',
            name='adaptive_max_abs_residual',
        ),
        migrations.RemoveField(
            model_name='greenhousecontrolprofile',
            name='adaptive_enabled',
        ),
        migrations.RemoveField(
            model_name='greenhousecontrolprofile',
            name='adaptive_rls_window',
        ),
        migrations.RemoveField(
            model_name='greenhousecontrolprofile',
            name='adaptive_max_abs_residual',
        ),
        migrations.RemoveField(
            model_name='ampcrecommendation',
            name='rls_update_count',
        ),
        migrations.RemoveField(
            model_name='ampcrecommendation',
            name='rls_skipped_count',
        ),
    ]
