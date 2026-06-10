from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = Path(
    'migrations/versions/d9e8f7a6b5c4_link_analytics_reports_explicitly_to_datasets.py'
)


def load_migration_module():
    spec = spec_from_file_location('link_analytics_reports_explicitly_to_datasets', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_dataset_link_migration_targets_expected_revision_chain():
    module = load_migration_module()

    assert module.revision == 'd9e8f7a6b5c4'
    assert module.down_revision == 'c8f2d3e4a5b6'


def test_report_dataset_link_migration_uses_postgresql_safe_fk_names():
    content = MIGRATION_PATH.read_text()

    assert 'fk_analytics_report_defs_dataset_id' in content
    assert 'fk_analytics_report_vers_dataset_ver_id' in content
    assert 'fk_analytics_report_versions_dataset_version_id_analytics_dataset_versions' not in content

    for constraint_name in (
        'fk_analytics_report_defs_dataset_id',
        'fk_analytics_report_vers_dataset_ver_id',
    ):
        assert len(constraint_name) <= 63
