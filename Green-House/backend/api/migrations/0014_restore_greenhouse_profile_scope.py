from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        [table_name],
    )
    return cursor.fetchone()[0] > 0


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


def index_exists(cursor, table_name, index_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        """,
        [table_name, index_name],
    )
    return cursor.fetchone()[0] > 0


def add_column_if_missing(cursor, table_name, column_name, column_sql):
    if table_exists(cursor, table_name) and not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN {column_sql}")


def create_greenhouse_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `greenhouses` (
            `id` bigint NOT NULL AUTO_INCREMENT,
            `created_at` datetime(6) NOT NULL,
            `updated_at` datetime(6) NOT NULL,
            `owner_id` integer NOT NULL,
            `name` varchar(120) NOT NULL DEFAULT 'Main greenhouse',
            `location` varchar(255) NOT NULL DEFAULT '',
            `is_active` bool NOT NULL DEFAULT 1,
            `notes` longtext NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uq_greenhouse_owner_name` (`owner_id`, `name`),
            KEY `greenhouses_owner_id_idx` (`owner_id`)
        )
        """
    )


def ensure_system_user(cursor):
    cursor.execute("SELECT `id` FROM `auth_user` ORDER BY `id` LIMIT 1")
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO `auth_user`
            (`password`, `last_login`, `is_superuser`, `username`, `first_name`,
             `last_name`, `email`, `is_staff`, `is_active`, `date_joined`)
        VALUES
            ('!', NULL, 0, 'system-greenhouse', '', '', '', 0, 1, NOW(6))
        """
    )
    return cursor.lastrowid


def ensure_greenhouse(cursor, owner_id, name):
    cursor.execute(
        """
        SELECT `id`
        FROM `greenhouses`
        WHERE `owner_id` = %s AND `name` = %s
        LIMIT 1
        """,
        [owner_id, name],
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO `greenhouses`
            (`created_at`, `updated_at`, `owner_id`, `name`, `location`, `is_active`, `notes`)
        VALUES
            (NOW(6), NOW(6), %s, %s, '', 1, '')
        """,
        [owner_id, name],
    )
    return cursor.lastrowid


def greenhouse_ids_with_existing_data(cursor):
    counts = {}
    for table_name in (
        'api_sensordata',
        'api_estimationcycle',
        'api_ampcrecommendation',
        'experiment_runs',
    ):
        if not table_exists(cursor, table_name) or not column_exists(cursor, table_name, 'greenhouse_id'):
            continue
        cursor.execute(
            f"""
            SELECT `greenhouse_id`, COUNT(*)
            FROM `{table_name}`
            WHERE `greenhouse_id` IS NOT NULL
            GROUP BY `greenhouse_id`
            """
        )
        for greenhouse_id, count in cursor.fetchall():
            counts[greenhouse_id] = counts.get(greenhouse_id, 0) + count

    return [
        greenhouse_id
        for greenhouse_id, _ in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def sync_greenhouse_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        create_greenhouse_table(cursor)

        add_column_if_missing(
            cursor,
            'greenhouse_control_profiles',
            'greenhouse_id',
            "`greenhouse_id` bigint NULL",
        )
        add_column_if_missing(cursor, 'experiment_runs', 'greenhouse_id', "`greenhouse_id` bigint NULL")
        add_column_if_missing(cursor, 'api_sensordata', 'greenhouse_id', "`greenhouse_id` bigint NULL")
        add_column_if_missing(cursor, 'api_estimationcycle', 'greenhouse_id', "`greenhouse_id` bigint NULL")
        add_column_if_missing(cursor, 'api_ampcrecommendation', 'greenhouse_id', "`greenhouse_id` bigint NULL")

        owner_id = ensure_system_user(cursor)
        main_greenhouse_id = ensure_greenhouse(cursor, owner_id, 'Main greenhouse')
        profile_greenhouse_ids = greenhouse_ids_with_existing_data(cursor) or [main_greenhouse_id]

        if table_exists(cursor, 'greenhouse_control_profiles'):
            cursor.execute(
                """
                SELECT `id`
                FROM `greenhouse_control_profiles`
                WHERE `greenhouse_id` IS NULL
                ORDER BY `id`
                """
            )
            profile_ids = [row[0] for row in cursor.fetchall()]
            for index, profile_id in enumerate(profile_ids):
                if index < len(profile_greenhouse_ids):
                    greenhouse_id = profile_greenhouse_ids[index]
                else:
                    greenhouse_id = ensure_greenhouse(
                        cursor,
                        owner_id,
                        f'Legacy greenhouse {profile_id}',
                    )
                singleton_key = f'gh-{greenhouse_id}'
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM `greenhouse_control_profiles`
                    WHERE `singleton_key` = %s AND `id` <> %s
                    """,
                    [singleton_key, profile_id],
                )
                if cursor.fetchone()[0] > 0:
                    singleton_key = f'profile-{profile_id}'
                cursor.execute(
                    """
                    UPDATE `greenhouse_control_profiles`
                    SET `greenhouse_id` = %s,
                        `singleton_key` = %s
                    WHERE `id` = %s
                    """,
                    [greenhouse_id, singleton_key, profile_id],
                )

            if not index_exists(cursor, 'greenhouse_control_profiles', 'uq_greenhouse_control_profile_greenhouse'):
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX `uq_greenhouse_control_profile_greenhouse`
                    ON `greenhouse_control_profiles` (`greenhouse_id`)
                    """
                )

        for table_name in (
            'experiment_runs',
            'api_sensordata',
            'api_estimationcycle',
            'api_ampcrecommendation',
        ):
            if table_exists(cursor, table_name) and column_exists(cursor, table_name, 'greenhouse_id'):
                cursor.execute(
                    f"""
                    UPDATE `{table_name}`
                    SET `greenhouse_id` = %s
                    WHERE `greenhouse_id` IS NULL
                    """,
                    [main_greenhouse_id],
                )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0013_cleanup_legacy_ampc_kalman_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(sync_greenhouse_columns, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='Greenhouse',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('name', models.CharField(default='Main greenhouse', max_length=120)),
                        ('location', models.CharField(blank=True, max_length=255)),
                        ('is_active', models.BooleanField(default=True)),
                        ('notes', models.TextField(blank=True)),
                        ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='greenhouses', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'greenhouses',
                        'ordering': ['id'],
                    },
                ),
                migrations.AddConstraint(
                    model_name='greenhouse',
                    constraint=models.UniqueConstraint(fields=('owner', 'name'), name='uq_greenhouse_owner_name'),
                ),
                migrations.AddField(
                    model_name='experimentrun',
                    name='greenhouse',
                    field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='runs', to='api.greenhouse'),
                ),
                migrations.AddField(
                    model_name='sensordata',
                    name='greenhouse',
                    field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sensor_readings', to='api.greenhouse'),
                ),
                migrations.AddField(
                    model_name='estimationcycle',
                    name='greenhouse',
                    field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='estimation_cycles', to='api.greenhouse'),
                ),
                migrations.AddField(
                    model_name='greenhousecontrolprofile',
                    name='greenhouse',
                    field=models.OneToOneField(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='control_profile', to='api.greenhouse'),
                ),
                migrations.AddField(
                    model_name='ampcrecommendation',
                    name='greenhouse',
                    field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ampc_recommendations', to='api.greenhouse'),
                ),
            ],
        ),
    ]
