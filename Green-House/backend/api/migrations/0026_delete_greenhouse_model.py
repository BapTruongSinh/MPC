from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0025_pin_runtime_data_to_admin_owner'),
    ]

    operations = [
        migrations.DeleteModel(name='Greenhouse'),
    ]
