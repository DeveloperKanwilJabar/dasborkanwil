from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = Path(
    'migrations/versions/f1b2c3d4e5f6_allow_master_data_admin_level_for_data_registry_records.py'
)


def load_migration_module():
    spec = spec_from_file_location('allow_master_data_admin_level_for_data_registry_records', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_record_admin_level_migration_allows_master_data_records():
    module = load_migration_module()

    assert module.UPDATED_RECORD_ADMIN_LEVEL_CHECK == (
        "admin_level IN ('province', 'city_regency', 'district', 'village', 'master_data')"
    )


def test_record_admin_level_migration_keeps_legacy_downgrade_contract():
    module = load_migration_module()

    assert module.LEGACY_RECORD_ADMIN_LEVEL_CHECK == (
        "admin_level IN ('province', 'city_regency', 'district', 'village')"
    )
