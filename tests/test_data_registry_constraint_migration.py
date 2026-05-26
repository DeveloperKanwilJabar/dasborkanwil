from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = Path(
    'migrations/versions/c4d7a9e2b1f0_backfill_data_registry_materialization_metadata.py'
)


def load_migration_module():
    spec = spec_from_file_location('expand_data_registry_constraints_for_master_data', MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_data_registry_constraint_migration_expands_registry_types_and_shapes():
    module = load_migration_module()

    assert module.UPDATED_REGISTRY_TYPE_CHECK == "registry_type IN ('geo', 'master_data')"
    assert module.UPDATED_REGISTRY_DATA_SHAPE_CHECK == (
        "data_shape IN ('hierarchical_geo', 'geojson', 'hierarchical', 'tabular')"
    )


def test_data_registry_constraint_migration_keeps_legacy_downgrade_contract():
    module = load_migration_module()

    assert module.LEGACY_REGISTRY_TYPE_CHECK == "registry_type IN ('geo')"
    assert module.LEGACY_REGISTRY_DATA_SHAPE_CHECK == "data_shape IN ('hierarchical_geo', 'geojson')"
