# Generated manually for smart_greenhouse project
# DB state: api_device and api_greenhouse tables do NOT exist (DB diverged from migration state)
# This migration uses SeparateDatabaseAndState to handle the mismatch

from django.db import migrations, models


def drop_index_if_exists(apps, schema_editor):
    """Drop est_greenhouse_ts_idx if it exists."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE table_schema = DATABASE()
            AND table_name = 'api_estimationcycle'
            AND index_name = 'est_greenhouse_ts_idx'
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute("DROP INDEX est_greenhouse_ts_idx ON api_estimationcycle")


def drop_column_if_exists(table, column):
    """Return a RunPython-compatible function that drops a column if it exists."""
    def _drop(apps, schema_editor):
        db = schema_editor.connection
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE table_schema = DATABASE()
                AND table_name = %s
                AND column_name = %s
            """, [table, column])
            if cursor.fetchone()[0] > 0:
                cursor.execute(f"ALTER TABLE `{table}` DROP COLUMN `{column}`")
    return _drop


def add_column_if_not_exists(table, column, sql_def):
    """Return a RunPython-compatible function that adds a column if not exists."""
    def _add(apps, schema_editor):
        db = schema_editor.connection
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE table_schema = DATABASE()
                AND table_name = %s
                AND column_name = %s
            """, [table, column])
            if cursor.fetchone()[0] == 0:
                cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN {sql_def}")
    return _add


def create_devicecommand_table(apps, schema_editor):
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_devicecommand (
                id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME(6) NOT NULL,
                updated_at DATETIME(6) NOT NULL,
                device_code VARCHAR(50) NOT NULL,
                command VARCHAR(50) NOT NULL,
                `value` VARCHAR(50) NOT NULL DEFAULT '',
                payload JSON NOT NULL,
                `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
                acked_at DATETIME(6) NULL,
                INDEX cmd_status_created_idx (`status`, created_at),
                INDEX api_devicecommand_device_code_idx (device_code)
            )
        """)


def create_devicestate_table(apps, schema_editor):
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_devicestate (
                id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME(6) NOT NULL,
                updated_at DATETIME(6) NOT NULL,
                device_code VARCHAR(50) NOT NULL,
                is_on TINYINT(1) NOT NULL DEFAULT 0,
                desired_on TINYINT(1) NOT NULL DEFAULT 0,
                last_command VARCHAR(50) NOT NULL DEFAULT '',
                `last_value` VARCHAR(50) NOT NULL DEFAULT '',
                extra JSON NOT NULL,
                UNIQUE KEY uq_devicestate_device_code (device_code)
            )
        """)


def seed_singleton_key(apps, schema_editor):
    """Set singleton_key on existing GreenhouseControlProfile rows."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE table_schema = DATABASE()
            AND table_name = 'greenhouse_control_profiles'
            AND column_name = 'singleton_key'
        """)
        col_exists = cursor.fetchone()[0] > 0
        if col_exists:
            cursor.execute("""
                UPDATE greenhouse_control_profiles
                SET singleton_key = 'main'
                WHERE singleton_key = '' OR singleton_key IS NULL
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_scope_device_code_per_greenhouse'),
    ]

    operations = [
        # ── 1. Update migration STATE only (no DB ops) for tables that don't exist in DB ──
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(model_name='device', name='greenhouse'),
                migrations.RemoveField(model_name='greenhouse', name='owner'),
                migrations.RemoveField(model_name='ampcrecommendation', name='greenhouse'),
                migrations.RemoveField(model_name='ampcschedulerstate', name='greenhouse'),
                migrations.RemoveField(model_name='controlstate', name='greenhouse'),
                migrations.RemoveField(model_name='devicecommand', name='device'),
                migrations.RemoveField(model_name='devicestate', name='device'),
                migrations.RemoveField(model_name='estimationcycle', name='greenhouse'),
                migrations.RemoveField(model_name='experimentrun', name='greenhouse'),
                migrations.RemoveField(model_name='greenhousecontrolprofile', name='greenhouse'),
                migrations.RemoveField(model_name='sensordata', name='greenhouse'),
            ],
        ),

        # ── 2. Xóa index est_greenhouse_ts_idx nếu tồn tại (dùng RunPython để IF EXISTS safe) ──
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_index_if_exists, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name='estimationcycle',
                    name='est_greenhouse_ts_idx',
                ),
            ],
        ),

        # ── 3. AlterModelOptions GreenhouseControlProfile ──
        migrations.AlterModelOptions(
            name='greenhousecontrolprofile',
            options={},
        ),

        # ── 4. Alert: xóa cột device_name (nếu có) và thêm device_code ──
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    drop_column_if_exists('api_alert', 'device_name'),
                    migrations.RunPython.noop,
                ),
                migrations.RunPython(
                    add_column_if_not_exists(
                        'api_alert', 'device_code',
                        "`device_code` VARCHAR(50) NOT NULL DEFAULT ''"
                    ),
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='alert', name='device'),
                migrations.AddField(
                    model_name='alert',
                    name='device_code',
                    field=models.CharField(blank=True, default='', max_length=50),
                ),
            ],
        ),

        # ── 5. Tạo bảng api_devicecommand (CREATE IF NOT EXISTS) ──
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_devicecommand_table, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='devicecommand',
                    name='device_code',
                    field=models.CharField(db_index=True, default='unknown', max_length=50),
                    preserve_default=False,
                ),
            ],
        ),

        # ── 6. Tạo bảng api_devicestate (CREATE IF NOT EXISTS) ──
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_devicestate_table, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='devicestate',
                    name='device_code',
                    field=models.CharField(default='unknown', max_length=50, unique=True),
                    preserve_default=False,
                ),
            ],
        ),

        # ── 7. Thêm singleton_key vào GreenhouseControlProfile ──
        migrations.AddField(
            model_name='greenhousecontrolprofile',
            name='singleton_key',
            field=models.CharField(default='main', max_length=20, unique=True),
        ),

        # ── 8. Seed singleton_key cho records đã tồn tại ──
        migrations.RunPython(seed_singleton_key, migrations.RunPython.noop),

        # ── 9. Xóa model Device và Greenhouse (chỉ update state, DB không có) ──
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Device'),
                migrations.DeleteModel(name='Greenhouse'),
            ],
        ),
    ]
