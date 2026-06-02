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


def test_import_batch_type_migration_allows_manual_entry_batches():
    module = load_migration_module()

    assert module.UPDATED_IMPORT_BATCH_TYPE_CHECK == (
        "batch_type IN ('file_upload', 'manual_seed', 'manual_entry', 'sync_snapshot')"
    )


def test_import_batch_type_migration_keeps_legacy_downgrade_contract():
    module = load_migration_module()

    assert module.LEGACY_IMPORT_BATCH_TYPE_CHECK == (
        "batch_type IN ('file_upload', 'manual_seed', 'sync_snapshot')"
    )
