from pathlib import Path
from types import SimpleNamespace

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def test_data_registry_web_import_console_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/data-registries/versions/<int:version_id>/import-console',
        '/data-registries/import-batches/<int:batch_id>/import-console',
        '/data-registries/import-batches/<int:batch_id>/validate',
        '/data-registries/import-batches/<int:batch_id>/materialize',
        '/data-registries/import-batches/<int:batch_id>/errors.xlsx',
    ]

    for route in expected_routes:
        assert route in rules


def test_data_registry_version_import_console_page_returns_batch_list(monkeypatch):
    app = create_app('testing')

    version = SimpleNamespace(
        id=31,
        uuid='version-uuid',
        registry_id=10,
        version_number=2,
        status='draft',
        source_snapshot={'source_name': 'diskominfo-jabar'},
        materialization_metadata={'record_count': 4, 'batch_id': 101},
        freshness_status='stale',
        materialized_at='2026-05-23T22:30:00+00:00',
    )
    batches = [
        SimpleNamespace(
            id=101,
            uuid='batch-uuid',
            original_filename='wilayah.xlsx',
            status='materialized',
            total_rows=3,
            valid_rows=2,
            error_rows=1,
            duplicate_rows=1,
            materialization_summary={'record_count': 4},
            validation_summary={'error_rows': 1},
        )
    ]

    class StubVersionService:
        def get_version_detail(self, version_id):
            assert version_id == 31
            return {'version': version, 'batches': batches}

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)

    client = app.test_client()
    response = client.get('/data-registries/versions/31/import-console')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Import Console Registry' in html
    assert 'wilayah.xlsx' in html
    assert 'Buka Console Batch' in html
    assert 'Status Version' in html
    assert 'Draft Kerja' in html
    assert 'Butuh Refresh' in html
    assert '23/05/2026 22:30 UTC' in html
    assert '1 duplikat perlu perhatian' in html
    assert 'Perlu review error/duplicate sebelum batch dipakai ulang.' in html


def test_data_registry_batch_import_console_page_returns_validate_contract(monkeypatch):
    app = create_app('testing')

    batch = SimpleNamespace(
        id=101,
        uuid='batch-uuid',
        registry_id=10,
        registry_version_id=31,
        original_filename='wilayah.xlsx',
        status='materialized',
        total_rows=3,
        mapped_rows=3,
        valid_rows=2,
        error_rows=1,
        duplicate_rows=0,
        skipped_rows=0,
        source_headers=['Kode', 'Nama'],
        validation_summary={
            'valid_rows': 2,
            'error_rows': 1,
            'duplicate_rows': 0,
            'required_field_errors': 1,
        },
        materialization_summary={
            'record_count': 4,
            'source_row_count': 1,
            'materialization_contract': 'wilayah_v1',
            'materialized_record_count': 4,
        },
        created_at='2026-05-23T22:10:00+00:00',
        materialized_at='2026-05-23T22:30:00+00:00',
    )
    version = SimpleNamespace(
        id=31,
        uuid='version-uuid',
        version_number=2,
        status='draft',
        mapping_spec={'materialization_contract': 'wilayah_v1'},
        materialization_metadata={
            'batch_id': 101,
            'record_count': 4,
            'source_row_count': 1,
            'materialization_contract': 'wilayah_v1',
        },
        materialized_at='2026-05-23T22:30:00+00:00',
        freshness_status='fresh',
    )
    rows = [
        SimpleNamespace(
            row_number=1,
            status='error',
            record_code_candidate='32.01',
            mapped_payload={'record_code': '32.01', 'label': 'Kabupaten A'},
            normalized_payload={},
            validation_errors={'label': ['required']},
        )
    ]

    class StubImportBatchService:
        def get_batch_detail(self, batch_id):
            assert batch_id == 101
            return {'batch': batch, 'version': version}

        def list_batch_rows(self, batch_id, status=None):
            assert batch_id == 101
            assert status is None
            return {'batch': batch, 'rows': rows}

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.get('/data-registries/import-batches/101/import-console')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Console Batch Import Registry' in html
    assert 'id="dataRegistryBatchValidateForm"' in html
    assert 'id="dataRegistryBatchMaterializeForm"' in html
    assert 'dataRegistryDownloadErrorWorkbookBtn' in html
    assert 'Materialisasi Batch' in html
    assert 'wilayah.xlsx' in html
    assert 'Kabupaten A' in html
    assert 'Status Batch' in html
    assert 'Siap dipakai untuk preview summary registry' in html
    assert '23/05/2026 22:30 UTC' in html
    assert 'Batch punya 1 error row dan 0 duplikat pada snapshot saat ini.' in html
    assert 'Sticky Ringkasan Batch' in html
    assert 'Mapped Payload Terbaca' in html
    assert 'Validation Errors Terbaca' in html
    assert 'record_code' in html
    assert 'label' in html
    assert 'required' in html
    assert 'fresh' in html
    assert 'Validation Summary' in html
    assert 'Materialization Summary' in html
    assert 'Required Field Errors' in html
    assert 'Materialized Record Count' in html
    assert 'wilayah_v1' in html
    assert 'bg-success-subtle text-success fs-12' in html
    assert 'bg-danger-subtle text-danger">error</span>' in html
    assert '<pre class="mb-0 fs-12 bg-light rounded p-3">' not in html


def test_data_registry_batch_import_console_supports_row_status_quick_filter(monkeypatch):
    app = create_app('testing')

    batch = SimpleNamespace(
        id=101,
        uuid='batch-uuid',
        registry_id=10,
        registry_version_id=31,
        original_filename='wilayah.xlsx',
        status='validated',
        total_rows=4,
        mapped_rows=4,
        valid_rows=2,
        error_rows=1,
        duplicate_rows=1,
        skipped_rows=0,
        source_headers=['Kode', 'Nama'],
        validation_summary={'valid_rows': 2, 'error_rows': 1, 'duplicate_rows': 1},
        materialization_summary={'record_count': 2},
        created_at='2026-05-23T22:10:00+00:00',
        materialized_at=None,
    )
    version = SimpleNamespace(
        id=31,
        uuid='version-uuid',
        version_number=2,
        status='draft',
        mapping_spec={'materialization_contract': 'wilayah_v1'},
        materialization_metadata={},
        materialized_at=None,
        freshness_status='stale',
    )
    rows = [
        SimpleNamespace(
            row_number=2,
            status='error',
            record_code_candidate='32.01.01',
            mapped_payload={'record_code': '32.01.01'},
            normalized_payload={},
            validation_errors={'name': ['Wajib diisi']},
        )
    ]

    class StubImportBatchService:
        def get_batch_detail(self, batch_id):
            assert batch_id == 101
            return {'batch': batch, 'version': version}

        def list_batch_rows(self, batch_id, status=None):
            assert batch_id == 101
            assert status == 'error'
            return {'batch': batch, 'rows': rows}

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.get('/data-registries/import-batches/101/import-console?status=error')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Filter cepat status row' in html
    assert 'Semua Row' in html
    assert 'Hanya Error' in html
    assert 'status=error' in html
    assert 'Menampilkan row dengan status error.' in html
    assert 'Wajib diisi' in html


def test_data_registry_batch_import_console_shows_contextual_back_to_version_cta(monkeypatch):
    app = create_app('testing')

    batch = SimpleNamespace(
        id=101,
        uuid='batch-uuid',
        registry_id=10,
        registry_version_id=31,
        original_filename='wilayah.xlsx',
        status='materialized',
        total_rows=4,
        mapped_rows=4,
        valid_rows=3,
        error_rows=1,
        duplicate_rows=1,
        skipped_rows=0,
        source_headers=['Kode', 'Nama'],
        validation_summary={'valid_rows': 3, 'error_rows': 1, 'duplicate_rows': 1},
        materialization_summary={'record_count': 3},
        created_at='2026-05-23T22:10:00+00:00',
        materialized_at='2026-05-23T22:30:00+00:00',
    )
    version = SimpleNamespace(
        id=31,
        uuid='version-uuid',
        version_number=2,
        status='draft',
        mapping_spec={'materialization_contract': 'wilayah_v1'},
        materialization_metadata={'record_count': 3},
        materialized_at='2026-05-23T22:30:00+00:00',
        freshness_status='fresh',
    )
    rows = []

    class StubImportBatchService:
        def get_batch_detail(self, batch_id):
            assert batch_id == 101
            return {'batch': batch, 'version': version}

        def list_batch_rows(self, batch_id, status=None):
            assert batch_id == 101
            assert status is None
            return {'batch': batch, 'rows': rows}

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.get('/data-registries/import-batches/101/import-console')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Kembali ke Version Console' in html
    assert 'Batch terakhir ini sudah Termaterialisasi dengan 1 error row dan 1 duplikat.' in html
    assert '/data-registries/versions/31/import-console' in html
    assert 'position-sticky top-0' in html


def test_data_registry_batch_import_console_download_error_workbook_returns_attachment(monkeypatch):
    app = create_app('testing')
    workbook = b'fake-data-registry-xlsx'

    class StubImportBatchService:
        def export_import_batch_errors(self, batch_id):
            assert batch_id == 101
            return {
                'filename': 'data-registry-v2-errors.xlsx',
                'content': workbook,
                'error_rows_count': 2,
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.get('/data-registries/import-batches/101/errors.xlsx')

    assert response.status_code == 200
    assert response.data == workbook
    assert 'attachment; filename=data-registry-v2-errors.xlsx' in response.headers['Content-Disposition']
    assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def test_data_registry_batch_import_console_validate_post_redirects_back(monkeypatch):
    app = create_app('testing')
    calls = []

    class StubImportValidationService:
        def validate_batch(self, batch_id, actor=None):
            calls.append((batch_id, actor))
            return {
                'batch': SimpleNamespace(
                    id=batch_id,
                    status='validated',
                    total_rows=3,
                    mapped_rows=3,
                    valid_rows=3,
                    error_rows=0,
                    duplicate_rows=0,
                    skipped_rows=0,
                    validation_summary={'valid_rows': 3},
                )
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportValidationService', StubImportValidationService)

    client = app.test_client()
    response = client.post('/data-registries/import-batches/101/validate')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/import-batches/101/import-console')
    assert calls and calls[0][0] == 101


def test_data_registry_batch_import_console_materialize_post_redirects_back(monkeypatch):
    app = create_app('testing')
    calls = []

    class StubMaterializationService:
        def materialize_import_batch(self, batch_id, actor=None):
            calls.append((batch_id, actor))
            return {
                'batch': SimpleNamespace(
                    id=batch_id,
                    status='materialized',
                    materialization_summary={
                        'record_count': 4,
                        'source_row_count': 1,
                        'materialization_contract': 'wilayah_v1',
                    },
                ),
                'version': SimpleNamespace(
                    id=31,
                    freshness_status='fresh',
                    materialization_metadata={'record_count': 4},
                ),
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryMaterializationService', StubMaterializationService)

    client = app.test_client()
    response = client.post('/data-registries/import-batches/101/materialize')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/import-batches/101/import-console')
    assert calls and calls[0][0] == 101


def test_data_registry_import_console_template_contains_validate_and_materialize_controls():
    template_content = Path('app/templates/pages/data_registry/import_batch_console.html').read_text(encoding='utf-8')
    version_template_content = Path('app/templates/pages/data_registry/import_console.html').read_text(encoding='utf-8')

    assert 'dataRegistryBatchValidateForm' in template_content
    assert 'dataRegistryBatchValidateBtn' in template_content
    assert 'dataRegistryBatchMaterializeForm' in template_content
    assert 'dataRegistryBatchMaterializeBtn' in template_content
    assert 'dataRegistryDownloadErrorWorkbookBtn' in template_content
    assert 'Ringkasan Materialisasi Registry Version' in template_content
    assert 'Status Batch' in template_content
    assert 'Batch siap dimaterialisasi ulang dengan aman' in template_content
    assert 'Preview cepat row staging untuk memastikan hasil validasi dan materialisasi sudah konsisten.' in template_content
    assert 'Sticky Ringkasan Batch' in template_content
    assert 'Mapped Payload Terbaca' in template_content
    assert 'Validation Errors Terbaca' in template_content
    assert 'position-sticky top-0' in template_content
    assert 'Status Version' in version_template_content
    assert 'Belum ada batch import untuk version ini. Upload/mapping berikutnya akan muncul di console ini.' in version_template_content
    assert 'duplikat perlu perhatian' in version_template_content
