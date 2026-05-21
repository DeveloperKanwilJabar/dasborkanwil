from app import create_app


def test_data_registry_models_have_expected_columns_and_relationships():
    app = create_app('testing')

    with app.app_context():
        from app.modules.data_registry.models import (
            DataRegistry,
            DataRegistryRecord,
            DataRegistryVersion,
        )

        registry_columns = DataRegistry.__table__.columns
        version_columns = DataRegistryVersion.__table__.columns
        record_columns = DataRegistryRecord.__table__.columns

        for column_name in [
            'uuid',
            'registry_slug',
            'registry_code',
            'name',
            'registry_type',
            'source_mode',
            'data_shape',
            'is_year_scoped',
            'status',
            'schema_meta',
        ]:
            assert column_name in registry_columns

        for column_name in [
            'uuid',
            'registry_id',
            'version_number',
            'status',
            'schema_json',
            'mapping_spec',
            'source_snapshot',
            'published_at',
            'freshness_status',
        ]:
            assert column_name in version_columns

        for column_name in [
            'uuid',
            'registry_id',
            'registry_version_id',
            'parent_record_id',
            'record_key',
            'record_code',
            'external_code',
            'label',
            'normalized_label',
            'admin_level',
            'city_regency_kind',
            'province_code',
            'city_regency_code',
            'district_code',
            'village_code',
            'village_adm_status',
            'centroid_lat',
            'centroid_lng',
            'geometry_json',
            'payload',
            'source_snapshot',
        ]:
            assert column_name in record_columns

        assert DataRegistryVersion.registry.property.mapper.class_ is DataRegistry
        assert DataRegistry.versions.property.mapper.class_ is DataRegistryVersion
        assert DataRegistryRecord.registry.property.mapper.class_ is DataRegistry
        assert DataRegistryRecord.registry_version.property.mapper.class_ is DataRegistryVersion
        assert DataRegistryRecord.parent.property.mapper.class_ is DataRegistryRecord
        assert DataRegistryRecord.children.property.mapper.class_ is DataRegistryRecord
