from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = Path(
    'migrations/versions/c4d7a9e2b1f0_backfill_data_registry_materialization_metadata.py'
)


def load_migration_module():
    spec = spec_from_file_location('backfill_data_registry_materialization_metadata', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_legacy_materialization_summary_prefers_batch_contract_and_counts():
    module = load_migration_module()

    projection = {
        'record_count': 4,
        'source_row_count': 1,
        'batch_contract': 'wilayah_v1',
        'version_contract': 'generic_v1',
    }

    assert module.build_legacy_materialization_summary(projection) == {
        'record_count': 4,
        'source_row_count': 1,
        'materialization_contract': 'wilayah_v1',
    }


def test_build_legacy_version_materialization_metadata_carries_batch_context():
    module = load_migration_module()

    projection = {
        'batch_id': 101,
        'batch_uuid': 'batch-uuid',
        'source_name': 'diskominfo-jabar',
        'record_count': 4,
        'source_row_count': 1,
        'batch_contract': None,
        'version_contract': 'generic_v1',
    }

    assert module.build_legacy_version_materialization_metadata(projection) == {
        'materialization_contract': 'generic_v1',
        'source_row_count': 1,
        'record_count': 4,
        'batch_id': 101,
        'batch_uuid': 'batch-uuid',
        'source_name': 'diskominfo-jabar',
    }


def test_build_legacy_version_backfill_patch_marks_materialized_versions_fresh():
    module = load_migration_module()

    projection = {
        'version_id': 31,
        'batch_id': 101,
        'record_count': 4,
        'source_row_count': 1,
        'batch_materialized_at': None,
        'batch_updated_at': '2026-05-22T11:30:00+00:00',
        'batch_created_at': '2026-05-22T10:00:00+00:00',
        'version_updated_at': '2026-05-22T11:31:00+00:00',
        'version_created_at': '2026-05-22T09:00:00+00:00',
        'batch_contract': 'wilayah_v1',
        'version_contract': 'generic_v1',
        'batch_uuid': 'batch-uuid',
        'source_name': 'diskominfo-jabar',
    }

    patch = module.build_legacy_version_backfill_patch(projection)

    assert patch['freshness_status'] == 'fresh'
    assert patch['materialized_at'] == '2026-05-22T11:30:00+00:00'
    assert patch['materialized_watermark'] == 'legacy-backfill:batch:101:records:4:rows:1'
    assert patch['freshness_signature'] == 'legacy-backfill:version:31:batch:101:records:4:rows:1'
    assert patch['materialization_metadata']['batch_uuid'] == 'batch-uuid'
