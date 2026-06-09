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


def repair_devicecommand_device_code(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if not _column_exists(cursor, "api_devicecommand", "device_code"):
            cursor.execute(
                "ALTER TABLE api_devicecommand "
                "ADD COLUMN device_code VARCHAR(50) NOT NULL DEFAULT 'legacy'"
            )

        if not _index_exists(cursor, "api_devicecommand", "api_devicecommand_device_code_idx"):
            cursor.execute(
                "CREATE INDEX api_devicecommand_device_code_idx "
                "ON api_devicecommand (device_code)"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0017_repair_devicestate_device_code"),
    ]

    operations = [
        migrations.RunPython(repair_devicecommand_device_code, migrations.RunPython.noop),
    ]
