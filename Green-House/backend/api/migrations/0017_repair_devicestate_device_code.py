from django.db import migrations


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        [table, column],
    )
    return cursor.fetchone()[0] > 0


def _index_exists(cursor, table: str, index: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        """,
        [table, index],
    )
    return cursor.fetchone()[0] > 0


def _drop_foreign_keys_on_column(cursor, table: str, column: str) -> None:
    cursor.execute(
        """
        SELECT constraint_name
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
          AND referenced_table_name IS NOT NULL
        """,
        [table, column],
    )
    for (constraint_name,) in cursor.fetchall():
        cursor.execute(f"ALTER TABLE {table} DROP FOREIGN KEY {constraint_name}")


def repair_devicestate_device_code(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if not _column_exists(cursor, "api_devicestate", "device_code"):
            cursor.execute("ALTER TABLE api_devicestate ADD COLUMN device_code VARCHAR(50) NULL")

        cursor.execute(
            """
            UPDATE api_devicestate
            SET device_code = CONCAT('legacy-', id)
            WHERE device_code IS NULL OR device_code = ''
            """
        )
        cursor.execute("ALTER TABLE api_devicestate MODIFY device_code VARCHAR(50) NOT NULL")

        if _column_exists(cursor, "api_devicestate", "device_id"):
            _drop_foreign_keys_on_column(cursor, "api_devicestate", "device_id")
            cursor.execute("ALTER TABLE api_devicestate DROP COLUMN device_id")

        if not _index_exists(cursor, "api_devicestate", "uq_devicestate_device_code"):
            cursor.execute(
                "CREATE UNIQUE INDEX uq_devicestate_device_code "
                "ON api_devicestate (device_code)"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0016_remove_mpc_adaptive_rls_fields"),
    ]

    operations = [
        migrations.RunPython(repair_devicestate_device_code, migrations.RunPython.noop),
    ]
