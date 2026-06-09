from django.db import migrations


def _table_names(schema_editor):
    return set(schema_editor.connection.introspection.table_names())


def _columns(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        return {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }


def _constraints(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        return schema_editor.connection.introspection.get_constraints(cursor, table_name)


def _remove_field_if_present(schema_editor, model, field_name):
    table_name = model._meta.db_table
    if table_name not in _table_names(schema_editor):
        return

    field = model._meta.get_field(field_name)
    if field.column not in _columns(schema_editor, table_name):
        return

    for name, details in _constraints(schema_editor, table_name).items():
        if details['check'] and field.column in details['columns']:
            schema_editor.execute(schema_editor._delete_check_sql(model, name))
    schema_editor.remove_field(model, field)


def _remove_estimation_run_metadata(schema_editor, model):
    table_name = model._meta.db_table
    if table_name not in _table_names(schema_editor):
        return

    existing = _constraints(schema_editor, table_name)
    for constraint in model._meta.constraints:
        if constraint.name in existing:
            schema_editor.remove_constraint(model, constraint)
    for index in model._meta.indexes:
        if index.name == 'est_run_ts_idx' and index.name in existing:
            schema_editor.remove_index(model, index)
    _remove_field_if_present(schema_editor, model, 'run')


def remove_legacy_database_objects(apps, schema_editor):
    estimation = apps.get_model('api', 'EstimationCycle')
    recommendation = apps.get_model('api', 'AMPCRecommendation')
    profile = apps.get_model('api', 'GreenhouseControlProfile')

    _remove_estimation_run_metadata(schema_editor, estimation)
    _remove_field_if_present(schema_editor, recommendation, 'run')
    _remove_field_if_present(schema_editor, recommendation, 'used_today_pump_seconds')
    _remove_field_if_present(schema_editor, profile, 'cost_daily_cap_excess')
    _remove_field_if_present(schema_editor, profile, 'soft_daily_pump_cap_seconds')

    tables = _table_names(schema_editor)
    for model_name in (
        'EvaluationSummary',
        'ExperimentConfig',
        'ExperimentRun',
        'ControlProfile',
    ):
        model = apps.get_model('api', model_name)
        if model._meta.db_table in tables:
            schema_editor.delete_model(model)
            tables.remove(model._meta.db_table)


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0019_set_pump_flow_default_to_001'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    remove_legacy_database_objects,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(name='ControlProfile'),
                migrations.RemoveField(model_name='evaluationsummary', name='run'),
                migrations.RemoveField(model_name='experimentconfig', name='run'),
                migrations.RemoveField(model_name='experimentrun', name='greenhouse'),
                migrations.RemoveConstraint(
                    model_name='estimationcycle',
                    name='uq_api_est_run_cycle',
                ),
                migrations.RemoveConstraint(
                    model_name='estimationcycle',
                    name='uq_api_est_run_dedupe',
                ),
                migrations.RemoveIndex(
                    model_name='estimationcycle',
                    name='est_run_ts_idx',
                ),
                migrations.RemoveField(model_name='ampcrecommendation', name='run'),
                migrations.RemoveField(
                    model_name='ampcrecommendation',
                    name='used_today_pump_seconds',
                ),
                migrations.RemoveField(model_name='estimationcycle', name='run'),
                migrations.RemoveField(
                    model_name='greenhousecontrolprofile',
                    name='cost_daily_cap_excess',
                ),
                migrations.RemoveField(
                    model_name='greenhousecontrolprofile',
                    name='soft_daily_pump_cap_seconds',
                ),
                migrations.DeleteModel(name='EvaluationSummary'),
                migrations.DeleteModel(name='ExperimentConfig'),
                migrations.DeleteModel(name='ExperimentRun'),
            ],
        ),
    ]
