from app import create_app


def test_data_registry_models_have_expected_columns_and_relationships():
    app = create_app('testing')

    with app.app_context():
        from app.modules.data_registry.models import (
            DataRegistry,
            DataRegistryImportBatch,
            DataRegistryImportRow,
            DataRegistryRecord,
            DataRegistryVersion,
        )

        registry_columns = DataRegistry.__table__.columns
        import_batch_columns = DataRegistryImportBatch.__table__.columns
        import_row_columns = DataRegistryImportRow.__table__.columns
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
            'registry_version_id',
            'batch_type',
            'status',
            'original_filename',
            'mime_type',
            'reporting_year',
            'total_rows',
            'mapped_rows',
            'valid_rows',
            'error_rows',
            'duplicate_rows',
            'skipped_rows',
            'mapping_snapshot',
            'source_headers',
            'source_snapshot',
            'validation_summary',
            'materialized_at',
            'materialized_by',
            'materialized_by_uuid',
            'materialization_summary',
        ]:
            assert column_name in import_batch_columns

        for column_name in [
            'uuid',
            'import_batch_id',
            'row_number',
            'row_hash',
            'status',
            'record_key_candidate',
            'record_code_candidate',
            'duplicate_of_row_id',
            'raw_payload',
            'mapped_payload',
            'normalized_payload',
            'validation_errors',
            'validation_warnings',
            'lineage_snapshot',
        ]:
            assert column_name in import_row_columns

        for column_name in [
            'uuid',
            'registry_id',
            'version_number',
            'status',
            'schema_json',
            'mapping_spec',
            'source_snapshot',
            'published_at',
            'materialized_at',
            'materialization_metadata',
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
        assert DataRegistryVersion.import_batches.property.mapper.class_ is DataRegistryImportBatch
        assert DataRegistryImportBatch.registry.property.mapper.class_ is DataRegistry
        assert DataRegistryImportBatch.registry_version.property.mapper.class_ is DataRegistryVersion
        assert DataRegistryImportBatch.rows.property.mapper.class_ is DataRegistryImportRow
        assert DataRegistryImportRow.batch.property.mapper.class_ is DataRegistryImportBatch
        assert DataRegistryImportRow.duplicate_of_row.property.mapper.class_ is DataRegistryImportRow
        assert DataRegistryRecord.registry.property.mapper.class_ is DataRegistry
        assert DataRegistryRecord.registry_version.property.mapper.class_ is DataRegistryVersion
        assert DataRegistryRecord.parent.property.mapper.class_ is DataRegistryRecord
        assert DataRegistryRecord.children.property.mapper.class_ is DataRegistryRecord
