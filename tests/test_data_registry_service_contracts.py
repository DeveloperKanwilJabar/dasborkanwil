from app import create_app


def test_data_registry_repository_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.data_registry.repositories import (
            DataRegistryImportBatchRepository,
            DataRegistryImportRowRepository,
            DataRegistryRecordRepository,
            DataRegistryRepository,
            DataRegistryVersionRepository,
        )

        import_batch_repository = DataRegistryImportBatchRepository()
        import_row_repository = DataRegistryImportRowRepository()
        registry_repository = DataRegistryRepository()
        version_repository = DataRegistryVersionRepository()
        record_repository = DataRegistryRecordRepository()

        for method_name in [
            'get_by_slug',
            'get_active_by_slug',
            'list_by_status',
        ]:
            assert callable(getattr(registry_repository, method_name))

        for method_name in [
            'get_draft_version',
            'get_published_version',
            'get_next_version_number',
            'list_versions',
            'archive_published_others',
        ]:
            assert callable(getattr(version_repository, method_name))

        for method_name in [
            'get_by_id',
            'list_by_registry_version',
        ]:
            assert callable(getattr(import_batch_repository, method_name))

        for method_name in [
            'bulk_create',
            'list_by_batch',
            'count_by_batch_and_status',
        ]:
            assert callable(getattr(import_row_repository, method_name))

        for method_name in [
            'get_by_key',
            'get_by_code',
            'list_children',
            'list_by_level',
            'list_options',
            'list_feature_collection_records',
        ]:
            assert callable(getattr(record_repository, method_name))


def test_data_registry_service_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.data_registry.services import (
            DataRegistryImportBatchService,
            DataRegistryImportValidationService,
            DataRegistryMaterializationService,
            DataRegistryQueryService,
            DataRegistryService,
            DataRegistryVersionService,
        )

        import_batch_service = DataRegistryImportBatchService()
        import_validation_service = DataRegistryImportValidationService()
        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        query_service = DataRegistryQueryService()
        materialization_service = DataRegistryMaterializationService()

        for method_name in [
            'create_batch',
            'get_batch_detail',
            'list_batch_rows',
            'export_import_batch_errors',
        ]:
            assert callable(getattr(import_batch_service, method_name))

        for method_name in [
            'validate_batch',
        ]:
            assert callable(getattr(import_validation_service, method_name))

        for method_name in [
            'create_registry',
            'publish_registry',
            'get_registry_detail',
        ]:
            assert callable(getattr(registry_service, method_name))

        for method_name in [
            'create_draft_version',
            'publish_version',
            'get_published_version',
            'get_version_detail',
        ]:
            assert callable(getattr(version_service, method_name))

        for method_name in [
            'get_option_list',
            'get_lookup',
            'get_children',
            'get_tree',
            'get_feature_collection',
        ]:
            assert callable(getattr(query_service, method_name))

        for method_name in [
            'materialize_wilayah_rows',
            'materialize_import_batch',
        ]:
            assert callable(getattr(materialization_service, method_name))
