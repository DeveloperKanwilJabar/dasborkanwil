import pytest

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def assert_validation_error(response, expected_message):
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert expected_message in payload['message']
    assert payload['data']['error_type'] == 'validation_error'


def test_data_registry_import_api_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/api/v1/data-registry-versions/<int:version_id>',
        '/api/v1/data-registry-versions/<int:version_id>/import-batches',
        '/api/v1/data-registry-import-batches/<int:batch_id>',
        '/api/v1/data-registry-import-batches/<int:batch_id>/validate',
        '/api/v1/data-registry-import-batches/<int:batch_id>/rows',
        '/api/v1/data-registry-import-batches/<int:batch_id>/materialize',
    ]

    for route in expected_routes:
        assert route in rules


def test_create_import_batch_endpoint_returns_batch_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubImportBatchService:
        def create_batch(self, version_id, payload, actor=None):
            assert version_id == 31
            assert payload['batch_type'] == 'file_upload'
            return {
                'batch': {
                    'id': 101,
                    'uuid': 'batch-uuid',
                    'registry_id': 10,
                    'registry_version_id': 31,
                    'batch_type': 'file_upload',
                    'status': 'mapped',
                    'reporting_year': 2026,
                    'total_rows': 1,
                    'mapped_rows': 1,
                    'valid_rows': 0,
                    'error_rows': 0,
                    'duplicate_rows': 0,
                    'skipped_rows': 0,
                    'mapping_snapshot': payload['mapping_snapshot'],
                    'source_headers': payload['source_headers'],
                    'source_snapshot': payload['source_snapshot'],
                    'validation_summary': {},
                },
                'rows': [
                    {
                        'id': 201,
                        'row_number': 1,
                        'status': 'mapped',
                        'record_key_candidate': None,
                        'record_code_candidate': 'PRG-001',
                        'mapped_payload': {'record_code': 'PRG-001', 'label': 'Program A'},
                        'normalized_payload': {},
                        'validation_errors': {},
                        'validation_warnings': {},
                    }
                ],
            }

    monkeypatch.setattr(
        'app.api.v1.data_registries.routes.DataRegistryImportBatchService',
        StubImportBatchService,
    )

    response = client.post(
        '/api/v1/data-registry-versions/31/import-batches',
        json={
            'batch_type': 'file_upload',
            'mapping_snapshot': {'fields': {'record_code': {'source': 'Kode Program'}}},
            'source_headers': ['Kode Program'],
            'source_snapshot': {'source_name': 'pytest'},
            'rows': [{'Kode Program': 'PRG-001'}],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['batch']['status'] == 'mapped'
    assert payload['data']['rows'][0]['record_code_candidate'] == 'PRG-001'


def test_get_import_batch_detail_endpoint_returns_batch_and_version_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubImportBatchService:
        def get_batch_detail(self, batch_id):
            assert batch_id == 101
            return {
                'batch': {
                    'id': 101,
                    'uuid': 'batch-uuid',
                    'status': 'materialized',
                    'total_rows': 1,
                    'mapped_rows': 1,
                    'valid_rows': 1,
                    'error_rows': 0,
                    'duplicate_rows': 0,
                    'skipped_rows': 0,
                    'validation_summary': {},
                    'materialized_at': '2026-05-22T11:30:00+00:00',
                    'materialized_by': 7,
                    'materialized_by_uuid': 'actor-uuid',
                    'materialization_summary': {
                        'record_count': 4,
                        'source_row_count': 1,
                        'materialization_contract': 'wilayah_v1',
                    },
                },
                'version': {
                    'id': 31,
                    'uuid': 'version-uuid',
                    'registry_id': 10,
                    'version_number': 1,
                    'status': 'draft',
                    'schema_json': {},
                    'mapping_spec': {'materialization_contract': 'wilayah_v1'},
                    'source_snapshot': {'source_name': 'diskominfo-jabar'},
                    'publish_notes': None,
                    'published_at': None,
                    'materialized_at': '2026-05-22T11:30:00+00:00',
                    'materialization_metadata': {
                        'batch_id': 101,
                        'record_count': 4,
                        'source_row_count': 1,
                    },
                    'source_watermark': None,
                    'materialized_watermark': 'rows:1:2026-05-22T11:30:00+00:00',
                    'freshness_status': 'fresh',
                    'freshness_signature': 'sig',
                    'created_at': None,
                    'updated_at': None,
                },
            }

    monkeypatch.setattr(
        'app.api.v1.data_registries.routes.DataRegistryImportBatchService',
        StubImportBatchService,
    )

    response = client.get('/api/v1/data-registry-import-batches/101')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['batch']['id'] == 101
    assert payload['data']['batch']['materialization_summary']['record_count'] == 4
    assert payload['data']['version']['id'] == 31
    assert payload['data']['version']['freshness_status'] == 'fresh'


def test_get_version_detail_endpoint_returns_version_and_batch_summaries(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubVersionService:
        def get_version_detail(self, version_id):
            assert version_id == 31
            return {
                'version': {
                    'id': 31,
                    'uuid': 'version-uuid',
                    'registry_id': 10,
                    'version_number': 1,
                    'status': 'published',
                    'schema_json': {},
                    'mapping_spec': {'materialization_contract': 'wilayah_v1'},
                    'source_snapshot': {'source_name': 'diskominfo-jabar'},
                    'publish_notes': None,
                    'published_at': '2026-05-22T11:00:00+00:00',
                    'materialized_at': '2026-05-22T11:30:00+00:00',
                    'materialization_metadata': {
                        'batch_id': 101,
                        'record_count': 4,
                        'source_row_count': 1,
                    },
                    'source_watermark': None,
                    'materialized_watermark': 'rows:1:2026-05-22T11:30:00+00:00',
                    'freshness_status': 'fresh',
                    'freshness_signature': 'sig',
                    'created_at': None,
                    'updated_at': None,
                },
                'batches': [
                    {
                        'id': 101,
                        'uuid': 'batch-uuid',
                        'registry_id': 10,
                        'registry_version_id': 31,
                        'batch_type': 'file_upload',
                        'status': 'materialized',
                        'reporting_year': 2026,
                        'total_rows': 1,
                        'mapped_rows': 1,
                        'valid_rows': 1,
                        'error_rows': 0,
                        'duplicate_rows': 0,
                        'skipped_rows': 0,
                        'mapping_snapshot': {},
                        'source_headers': [],
                        'source_snapshot': {'source_name': 'diskominfo-jabar'},
                        'validation_summary': {},
                        'materialized_at': '2026-05-22T11:30:00+00:00',
                        'materialized_by': 7,
                        'materialized_by_uuid': 'actor-uuid',
                        'materialization_summary': {'record_count': 4},
                    }
                ],
            }

    monkeypatch.setattr(
        'app.api.v1.data_registries.routes.DataRegistryVersionService',
        StubVersionService,
    )

    response = client.get('/api/v1/data-registry-versions/31')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['version']['id'] == 31
    assert payload['data']['version']['materialization_metadata']['batch_id'] == 101
    assert payload['data']['version']['freshness_status'] == 'fresh'
    assert payload['data']['batches'][0]['status'] == 'materialized'


def test_validate_import_batch_endpoint_returns_validated_batch(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubImportValidationService:
        def validate_batch(self, batch_id, actor=None):
            assert batch_id == 101
            return {
                'batch': {
                    'id': 101,
                    'status': 'validated',
                    'valid_rows': 1,
                    'error_rows': 0,
                    'duplicate_rows': 0,
                    'skipped_rows': 0,
                    'validation_summary': {'field_error_counts': {}},
                }
            }

    monkeypatch.setattr(
        'app.api.v1.data_registries.routes.DataRegistryImportValidationService',
        StubImportValidationService,
    )

    response = client.post('/api/v1/data-registry-import-batches/101/validate', json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['batch']['status'] == 'validated'


def test_list_import_batch_rows_endpoint_returns_filtered_rows(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubImportBatchService:
        def list_batch_rows(self, batch_id, status=None):
            assert batch_id == 101
            assert status == 'error'
            return {
                'batch': {'id': 101, 'status': 'validated'},
                'rows': [
                    {
                        'id': 202,
                        'row_number': 2,
                        'status': 'error',
                        'record_key_candidate': None,
                        'record_code_candidate': 'PRG-002',
                        'mapped_payload': {'record_code': 'PRG-002'},
                        'normalized_payload': {},
                        'validation_errors': {'effective_date': 'invalid_date_format'},
                        'validation_warnings': {},
                    }
                ],
            }

    monkeypatch.setattr(
        'app.api.v1.data_registries.routes.DataRegistryImportBatchService',
        StubImportBatchService,
    )

    response = client.get('/api/v1/data-registry-import-batches/101/rows?status=error')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['rows'][0]['status'] == 'error'


def test_materialize_import_batch_endpoint_returns_materialization_summary(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubMaterializationService:
        def materialize_import_batch(self, batch_id, actor=None):
            assert batch_id == 101
            return {
                'batch': {
                    'id': 101,
                    'uuid': 'batch-uuid',
                    'status': 'materialized',
                    'total_rows': 2,
                    'valid_rows': 1,
                    'error_rows': 1,
                    'duplicate_rows': 0,
                    'skipped_rows': 0,
                    'validation_summary': {},
                    'materialized_at': '2026-05-22T11:30:00+00:00',
                    'materialized_by': 7,
                    'materialized_by_uuid': 'actor-uuid',
                    'materialization_summary': {
                        'record_count': 4,
                        'source_row_count': 1,
                        'materialization_contract': 'wilayah_v1',
                    },
                },
                'version': {
                    'id': 31,
                    'uuid': 'version-uuid',
                    'registry_id': 10,
                    'version_number': 1,
                    'status': 'draft',
                    'schema_json': {},
                    'mapping_spec': {'materialization_contract': 'wilayah_v1'},
                    'source_snapshot': {'source_name': 'diskominfo-jabar'},
                    'publish_notes': None,
                    'published_at': None,
                    'materialized_at': '2026-05-22T11:30:00+00:00',
                    'materialization_metadata': {
                        'materialization_contract': 'wilayah_v1',
                        'source_row_count': 1,
                        'record_count': 4,
                        'batch_id': 101,
                        'batch_uuid': 'batch-uuid',
                        'source_name': 'diskominfo-jabar',
                    },
                    'source_watermark': None,
                    'materialized_watermark': 'rows:1:2026-05-22T11:30:00+00:00',
                    'freshness_status': 'fresh',
                    'freshness_signature': 'sig',
                    'created_at': None,
                    'updated_at': None,
                },
                'materialization': {
                    'record_count': 4,
                    'source_row_count': 1,
                    'materialization_contract': 'wilayah_v1',
                },
            }

    monkeypatch.setattr(
        'app.api.v1.data_registries.routes.DataRegistryMaterializationService',
        StubMaterializationService,
    )

    response = client.post('/api/v1/data-registry-import-batches/101/materialize', json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['materialization']['record_count'] == 4
    assert payload['data']['materialization']['materialization_contract'] == 'wilayah_v1'
    assert payload['data']['batch']['id'] == 101
    assert payload['data']['batch']['status'] == 'materialized'
    assert payload['data']['batch']['materialization_summary']['record_count'] == 4
    assert payload['data']['version']['materialization_metadata']['batch_id'] == 101


@pytest.mark.parametrize(
    'method,endpoint,patch_target,service_method,expected_message,payload',
    [
        (
            'post',
            '/api/v1/data-registry-versions/31/import-batches',
            'app.api.v1.data_registries.routes.DataRegistryImportBatchService',
            'create_batch',
            'Target version registry harus draft.',
            {'rows': []},
        ),
        (
            'post',
            '/api/v1/data-registry-import-batches/101/validate',
            'app.api.v1.data_registries.routes.DataRegistryImportValidationService',
            'validate_batch',
            'Import batch tidak ditemukan.',
            {},
        ),
        (
            'get',
            '/api/v1/data-registry-import-batches/101/rows',
            'app.api.v1.data_registries.routes.DataRegistryImportBatchService',
            'list_batch_rows',
            'Import batch tidak ditemukan.',
            None,
        ),
        (
            'post',
            '/api/v1/data-registry-import-batches/101/materialize',
            'app.api.v1.data_registries.routes.DataRegistryMaterializationService',
            'materialize_import_batch',
            'Import batch harus berstatus validated sebelum materialization.',
            {},
        ),
    ],
)
def test_data_registry_import_api_validation_errors_return_standard_400(
    monkeypatch,
    method,
    endpoint,
    patch_target,
    service_method,
    expected_message,
    payload,
):
    app = create_app('testing')
    client = app.test_client()

    class StubService:
        pass

    def raise_validation_error(*args, **kwargs):
        raise ValueError(expected_message)

    setattr(StubService, service_method, raise_validation_error)
    monkeypatch.setattr(patch_target, StubService)

    http_call = getattr(client, method)
    response = http_call(endpoint, json=payload) if payload is not None else http_call(endpoint)

    assert_validation_error(response, expected_message)
