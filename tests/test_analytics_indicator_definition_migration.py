from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = Path(
    'migrations/versions/b7e1c2d3f4a5_add_analytics_indicator_definition_layer_v1.py'
)


def load_migration_module():
    spec = spec_from_file_location('add_analytics_indicator_definition_layer_v1', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analytics_indicator_definition_migration_exists_and_targets_dataset_foundation_head():
    assert MIGRATION_PATH.exists()

    module = load_migration_module()

    assert module.revision == 'b7e1c2d3f4a5'
    assert module.down_revision == 'a1b2c3d4e5f6'


def test_analytics_indicator_definition_migration_declares_expected_checks_and_tables():
    module = load_migration_module()

    assert 'pk' in module.ANALYTICS_REPORT_TYPE_CHECK
    assert 'renaksi' in module.ANALYTICS_REPORT_TYPE_CHECK
    assert 'draft' in module.ANALYTICS_DEFINITION_STATUS_CHECK
    assert 'published' in module.ANALYTICS_VERSION_STATUS_CHECK
    assert 'dataset_driven' in module.ANALYTICS_INDICATOR_SOURCE_MODE_CHECK
    assert 'manual_input' in module.ANALYTICS_INDICATOR_SOURCE_MODE_CHECK
    assert 'custom_formula' in module.ANALYTICS_INDICATOR_CALCULATION_TYPE_CHECK
    assert 'hybrid' in module.ANALYTICS_INDICATOR_TARGET_SOURCE_TYPE_CHECK
    assert 'multi_period' in module.ANALYTICS_PERIOD_MODE_CHECK
    assert 'last_value' in module.ANALYTICS_AGGREGATION_STRATEGY_CHECK

    migration_text = MIGRATION_PATH.read_text(encoding='utf-8')

    for table_name in [
        'analytics_report_definitions',
        'analytics_report_versions',
        'analytics_indicator_definitions',
        'analytics_indicator_versions',
        'analytics_report_version_indicators',
    ]:
        assert f"'{table_name}'" in migration_text


def test_analytics_indicator_definition_migration_declares_expected_indexes_and_foreign_keys():
    migration_text = MIGRATION_PATH.read_text(encoding='utf-8')

    assert 'ux_analytics_report_versions_one_cur_draft_per_def' in migration_text
    assert 'ux_analytics_report_versions_one_cur_pub_per_def' in migration_text
    assert 'ux_analytics_indicator_versions_one_cur_draft_per_def' in migration_text
    assert 'ux_analytics_indicator_versions_one_cur_pub_per_def' in migration_text

    assert "['dataset_id'], ['analytics_datasets.id']" in migration_text
    assert "['dataset_version_id'], ['analytics_dataset_versions.id']" in migration_text
    assert "['report_definition_id'], ['analytics_report_definitions.id']" in migration_text
    assert "['indicator_definition_id'], ['analytics_indicator_definitions.id']" in migration_text
