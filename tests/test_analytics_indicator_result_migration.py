from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = Path(
    'migrations/versions/c8f2d3e4a5b6_add_analytics_indicator_results_and_progress_v1.py'
)


def load_migration_module():
    spec = spec_from_file_location('add_analytics_indicator_results_and_progress_v1', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analytics_indicator_result_migration_exists_and_targets_definition_layer_head():
    assert MIGRATION_PATH.exists()

    module = load_migration_module()

    assert module.revision == 'c8f2d3e4a5b6'
    assert module.down_revision == 'b7e1c2d3f4a5'


def test_analytics_indicator_result_migration_declares_expected_checks_and_tables():
    module = load_migration_module()

    assert 'draft' in module.ANALYTICS_INDICATOR_RESULT_STATUS_CHECK
    assert 'published' in module.ANALYTICS_INDICATOR_RESULT_STATUS_CHECK
    assert 'in_progress' in module.ANALYTICS_COMPLETION_STATUS_CHECK
    assert 'completed' in module.ANALYTICS_COMPLETION_STATUS_CHECK
    assert 'draft' in module.ANALYTICS_PROGRESS_ENTRY_STATUS_CHECK
    assert 'pending' in module.ANALYTICS_PROGRESS_ITEM_STATUS_CHECK
    assert 'blocked' in module.ANALYTICS_PROGRESS_ITEM_STATUS_CHECK

    migration_text = MIGRATION_PATH.read_text(encoding='utf-8')

    for table_name in [
        'analytics_indicator_results',
        'analytics_indicator_progress_entries',
        'analytics_indicator_progress_items',
    ]:
        assert f"'{table_name}'" in migration_text


def test_analytics_indicator_result_migration_declares_expected_indexes_and_foreign_keys():
    migration_text = MIGRATION_PATH.read_text(encoding='utf-8')

    for expected in [
        'ix_analytics_indicator_results_reporting_year',
        'ix_analytics_indicator_results_reporting_period_id',
        'ix_analytics_indicator_results_dataset_run_id',
        'ix_analytics_indicator_results_completion_status',
        'ix_analytics_indicator_results_deleted_at',
        'ix_analytics_indicator_progress_entries_reporting_year',
        'ix_analytics_indicator_progress_entries_reporting_period_id',
        'ix_analytics_indicator_progress_entries_deleted_at',
        'ix_analytics_indicator_progress_items_deleted_at',
    ]:
        assert expected in migration_text

    assert "['dataset_run_id'], ['analytics_dataset_runs.id']" in migration_text
    assert "['reporting_period_id'], ['reporting_periods.id']" in migration_text
    assert "['progress_entry_id'], ['analytics_indicator_progress_entries.id']" in migration_text
