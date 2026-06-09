from django.db import migrations, models


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        [table_name, column_name],
    )
    return cursor.fetchone()[0] > 0


def drop_checks_referencing(cursor, table_name, column_names):
    cursor.execute(
        """
        SELECT tc.CONSTRAINT_NAME, cc.CHECK_CLAUSE
        FROM information_schema.TABLE_CONSTRAINTS tc
        JOIN information_schema.CHECK_CONSTRAINTS cc
          ON cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
         AND cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = DATABASE()
          AND tc.TABLE_NAME = %s
          AND tc.CONSTRAINT_TYPE = 'CHECK'
        """,
        [table_name],
    )
    constraints = cursor.fetchall()
    for constraint_name, clause in constraints:
        if not any(f"`{name}`" in clause or name in clause for name in column_names):
            continue
        try:
            cursor.execute(f"ALTER TABLE `{table_name}` DROP CHECK `{constraint_name}`")
        except Exception:
            cursor.execute(f"ALTER TABLE `{table_name}` DROP CONSTRAINT `{constraint_name}`")


def drop_indexes_referencing(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT DISTINCT INDEX_NAME
        FROM information_schema.STATISTICS
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
          AND INDEX_NAME != 'PRIMARY'
        """,
        [table_name, column_name],
    )
    for (index_name,) in cursor.fetchall():
        cursor.execute(f"DROP INDEX `{index_name}` ON `{table_name}`")


def drop_column_if_exists(cursor, table_name, column_name):
    if column_exists(cursor, table_name, column_name):
        drop_indexes_referencing(cursor, table_name, column_name)
        cursor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `{column_name}`")


def rename_column_if_exists(cursor, table_name, old_name, new_name, sql_type):
    if column_exists(cursor, table_name, new_name):
        return
    if column_exists(cursor, table_name, old_name):
        cursor.execute(
            f"ALTER TABLE `{table_name}` CHANGE `{old_name}` `{new_name}` {sql_type}"
        )


def cleanup_legacy_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        drop_checks_referencing(
            cursor,
            'greenhouse_control_profiles',
            [
                'pump_grid_seconds',
                'adaptive_bias_window',
                'adaptive_max_abs_bias',
            ],
        )
        drop_column_if_exists(cursor, 'greenhouse_control_profiles', 'greenhouse_id')
        drop_column_if_exists(cursor, 'greenhouse_control_profiles', 'theta_sat')
        drop_column_if_exists(cursor, 'greenhouse_control_profiles', 'pump_grid_seconds')
        rename_column_if_exists(
            cursor,
            'greenhouse_control_profiles',
            'adaptive_bias_window',
            'adaptive_rls_window',
            'integer UNSIGNED NOT NULL',
        )
        rename_column_if_exists(
            cursor,
            'greenhouse_control_profiles',
            'adaptive_max_abs_bias',
            'adaptive_max_abs_residual',
            'double precision NOT NULL',
        )

        drop_checks_referencing(cursor, 'api_controlprofile', ['pump_grid_seconds', 'adaptive_bias_window', 'adaptive_max_abs_bias'])
        drop_column_if_exists(cursor, 'api_controlprofile', 'pump_grid_seconds')
        rename_column_if_exists(
            cursor,
            'api_controlprofile',
            'adaptive_bias_window',
            'adaptive_rls_window',
            'integer UNSIGNED NOT NULL',
        )
        rename_column_if_exists(
            cursor,
            'api_controlprofile',
            'adaptive_max_abs_bias',
            'adaptive_max_abs_residual',
            'double precision NOT NULL',
        )

        drop_checks_referencing(cursor, 'experiment_configs', ['alpha'])
        rename_column_if_exists(
            cursor,
            'experiment_configs',
            'alpha',
            'forgetting_factor_b',
            'double precision NOT NULL',
        )

        drop_checks_referencing(cursor, 'api_ampcrecommendation', ['bias_correction', 'bias_window_count'])
        drop_column_if_exists(cursor, 'api_ampcrecommendation', 'bias_correction')
        rename_column_if_exists(
            cursor,
            'api_ampcrecommendation',
            'bias_window_count',
            'rls_update_count',
            'integer UNSIGNED NOT NULL',
        )
        if not column_exists(cursor, 'api_ampcrecommendation', 'rls_skipped_count'):
            cursor.execute(
                """
                ALTER TABLE `api_ampcrecommendation`
                ADD COLUMN `rls_skipped_count` integer UNSIGNED NOT NULL DEFAULT 0
                """
            )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_remove_greenhouse_device'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    cleanup_legacy_columns,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.RenameField(
                    model_name='experimentconfig',
                    old_name='alpha',
                    new_name='forgetting_factor_b',
                ),
                migrations.AlterField(
                    model_name='experimentconfig',
                    name='forgetting_factor_b',
                    field=models.FloatField(default=0.95),
                ),
                migrations.RemoveField(
                    model_name='controlprofile',
                    name='pump_grid_seconds',
                ),
                migrations.RenameField(
                    model_name='controlprofile',
                    old_name='adaptive_bias_window',
                    new_name='adaptive_rls_window',
                ),
                migrations.RenameField(
                    model_name='controlprofile',
                    old_name='adaptive_max_abs_bias',
                    new_name='adaptive_max_abs_residual',
                ),
                migrations.RemoveField(
                    model_name='greenhousecontrolprofile',
                    name='theta_sat',
                ),
                migrations.RemoveField(
                    model_name='greenhousecontrolprofile',
                    name='pump_grid_seconds',
                ),
                migrations.RenameField(
                    model_name='greenhousecontrolprofile',
                    old_name='adaptive_bias_window',
                    new_name='adaptive_rls_window',
                ),
                migrations.RenameField(
                    model_name='greenhousecontrolprofile',
                    old_name='adaptive_max_abs_bias',
                    new_name='adaptive_max_abs_residual',
                ),
                migrations.RemoveField(
                    model_name='ampcrecommendation',
                    name='bias_correction',
                ),
                migrations.RenameField(
                    model_name='ampcrecommendation',
                    old_name='bias_window_count',
                    new_name='rls_update_count',
                ),
                migrations.AddField(
                    model_name='ampcrecommendation',
                    name='rls_skipped_count',
                    field=models.PositiveIntegerField(default=0),
                ),
            ],
        ),
    ]
