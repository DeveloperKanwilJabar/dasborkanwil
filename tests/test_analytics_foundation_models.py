from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app import create_app
from app.core.extensions import db


MIGRATION_PATH = Path(
    'migrations/versions/a1b2c3d4e5f6_add_analytics_dataset_foundation_v1.py'
)


def load_migration_module():
    spec = spec_from_file_location('add_analytics_dataset_foundation_v1', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analytics_models_are_registered_in_app_metadata():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import (
            AnalyticsDataset,
            AnalyticsDatasetRun,
            AnalyticsDatasetVersion,
        )

        tables = db.metadata.tables

        assert 'analytics_datasets' in tables
        assert 'analytics_dataset_versions' in tables
        assert 'analytics_dataset_runs' in tables

        assert AnalyticsDataset.__tablename__ == 'analytics_datasets'
        assert AnalyticsDatasetVersion.__tablename__ == 'analytics_dataset_versions'
        assert AnalyticsDatasetRun.__tablename__ == 'analytics_dataset_runs'


def test_analytics_dataset_version_has_expected_uniques_and_partial_indexes():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import AnalyticsDatasetVersion

        table = AnalyticsDatasetVersion.__table__
        unique_constraints = {constraint.name for constraint in table.constraints if constraint.__class__.__name__ == 'UniqueConstraint'}
        index_names = {index.name for index in table.indexes}

        assert 'uq_analytics_dataset_versions_dataset_id_version_number' in unique_constraints
        assert 'uq_analytics_dataset_versions_id_dataset_id' in unique_constraints
        assert 'ux_analytics_dataset_versions_one_current_draft_per_dataset' in index_names
        assert 'ux_analytics_dataset_versions_one_current_published_per_dataset' in index_names


def test_analytics_dataset_run_has_composite_fk_to_matching_dataset_version():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import AnalyticsDatasetRun

        table = AnalyticsDatasetRun.__table__
        composite_fk = None
        for constraint in table.foreign_key_constraints:
            local_columns = tuple(column.name for column in constraint.columns)
            if local_columns == ('dataset_version_id', 'dataset_id'):
                composite_fk = constraint
                break

        assert composite_fk is not None
        remote_columns = sorted(element.column.name for element in composite_fk.elements)
        assert remote_columns == ['dataset_id', 'id']


def test_analytics_migration_foundation_targets_current_head_and_declares_checks():
    module = load_migration_module()

    assert module.down_revision == 'c4d7a9e2b1f0'
    assert 'draft' in module.ANALYTICS_DATASET_STATUS_CHECK
    assert 'published' in module.ANALYTICS_DATASET_VERSION_STATUS_CHECK
    assert 'queued' in module.ANALYTICS_RUN_STATUS_CHECK
    assert 'submissions.submitted_at' in module.ANALYTICS_FRESHNESS_SOURCE_TYPE_CHECK
