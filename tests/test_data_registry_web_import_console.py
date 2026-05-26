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
        '/data-registries/versions/<int:version_id>/import-mapping',
        '/data-registries/versions/<int:version_id>/manual-entry',
        '/data-registries/versions/<int:version_id>/field-designer',
        '/data-registries/versions/<int:version_id>/template.xlsx',
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

    class StubImportBatchService:
        def extract_importable_fields(self, version_or_schema):
            return [
                {'key': 'record_key', 'label': 'Record Key', 'required': True},
                {'key': 'record_code', 'label': 'Record Code', 'required': True, 'type': 'select', 'options': ['A', 'B']},
                {'key': 'label', 'label': 'Label', 'required': True},
            ]

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)
    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.get('/data-registries/versions/31/import-console')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Import Console Registry' in html
    assert 'Flow Ringkas Import' in html
    assert 'Pilih Jalur Entri' in html
    assert 'Entry Manual Cepat' in html
    assert 'Pakai ini kalau mau input 1 record dulu dari browser' in html
    assert 'Pilih Upload Excel' in html
    assert 'Referensi Kolom Registry' in html
    assert 'Field Designer Ringan' in html
    assert 'Export Template Excel' in html
    assert 'id="dataRegistryFieldDesignerForm"' in html
    assert 'name="field_key[]"' in html
    assert 'name="field_label[]"' in html
    assert 'name="field_type[]"' in html
    assert 'name="field_required[]"' in html
    assert 'name="field_options[]"' in html
    assert 'name="record_code"' in html
    assert 'Pilih Record Code' in html
    assert 'A, B' in html
    assert 'Siapkan batch staging' in html
    assert 'Validasi row dan cek error/duplikat' in html
    assert 'Materialisasi batch untuk refresh registry version' in html
    assert 'wilayah.xlsx' in html
    assert 'Buka Console Batch' in html
    assert 'Buka Shell Mapping' in html
    assert '/data-registries/versions/31/import-mapping' in html
    assert '/data-registries/versions/31/template.xlsx' in html
    assert 'Status Version' in html
    assert 'Draft Kerja' in html
    assert 'Butuh Refresh' in html
    assert '23/05/2026 22:30 UTC' in html
    assert '1 duplikat perlu perhatian' in html
    assert 'Perlu review error/duplicate sebelum batch dipakai ulang.' in html


def test_data_registry_field_designer_post_redirects_back_to_import_console(monkeypatch):
    app = create_app('testing')
    captured = {}

    class StubVersionService:
        def update_draft_schema_fields(self, version_id, fields, actor=None):
            captured['version_id'] = version_id
            captured['fields'] = fields
            captured['actor'] = actor
            return SimpleNamespace(id=version_id)

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)

    client = app.test_client()
    response = client.post(
        '/data-registries/versions/31/field-designer',
        data={
            'field_key[]': ['record_key', 'record_code', ''],
            'field_label[]': ['Record Key', 'Record Code', 'Ignored'],
            'field_type[]': ['text', 'select', 'text'],
            'field_options[]': ['', 'Aktif\nNonaktif', 'Tidak Dipakai'],
            'field_required[]': ['0'],
        },
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/versions/31/import-console')
    assert captured['version_id'] == 31
    assert captured['fields'] == [
        {'key': 'record_key', 'label': 'Record Key', 'type': 'text', 'required': True},
        {
            'key': 'record_code',
            'label': 'Record Code',
            'type': 'select',
            'required': False,
            'options': ['Aktif', 'Nonaktif'],
        },
    ]


def test_data_registry_template_download_returns_xlsx(monkeypatch):
    app = create_app('testing')
    registry = SimpleNamespace(id=10, registry_code='MASTER-PROGRAM', registry_slug='master.program', name='Master Program')
    version = SimpleNamespace(id=31, registry_id=10, version_number=2, registry=registry)

    class StubVersionService:
        def get_version_detail(self, version_id):
            assert version_id == 31
            return {'version': version, 'batches': []}

    class StubImportBatchService:
        def build_template_workbook(self, version_obj, registry=None):
            assert version_obj is version
            assert registry is version.registry
            return b'fake-registry-template'

        def build_template_filename(self, version_obj, registry=None):
            assert version_obj is version
            assert registry is version.registry
            return 'MASTER-PROGRAM-v2-template.xlsx'

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)
    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.get('/data-registries/versions/31/template.xlsx')

    assert response.status_code == 200
    assert response.data == b'fake-registry-template'
    assert 'attachment; filename=MASTER-PROGRAM-v2-template.xlsx' == response.headers['Content-Disposition']
    assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


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
    assert html.count('name="csrf_token"') >= 2
    assert 'Mode Operator Cepat' in html
    assert 'Review row → validasi batch → materialisasi registry.' in html
    assert 'Preview dibatasi 20 row pertama agar console tetap ringan dibaca.' in html
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
        source_snapshot={'source_name': 'diskominfo-jabar'},
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
    assert '/data-registries/versions/31/import-mapping' in html
    assert 'Upload Batch Baru' in html
    assert 'diskominfo-jabar' in html
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


def test_data_registry_batch_validate_post_requires_csrf_when_enabled():
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True)

    client = app.test_client()
    response = client.post('/data-registries/import-batches/101/validate')

    assert response.status_code == 400


def test_data_registry_batch_materialize_post_requires_csrf_when_enabled():
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True)

    client = app.test_client()
    response = client.post('/data-registries/import-batches/101/materialize')

    assert response.status_code == 400


def test_data_registry_mapping_shell_page_reads_workbook_and_renders_auto_mapping(monkeypatch):
    app = create_app('testing')

    version = SimpleNamespace(
        id=31,
        uuid='version-uuid',
        registry_id=10,
        version_number=2,
        status='draft',
        schema_json={'fields': [{'key': 'record_code', 'type': 'string', 'required': True, 'label': 'Record Code'}]},
        source_snapshot={'source_name': 'diskominfo-jabar'},
    )

    class StubVersionService:
        def get_version_detail(self, version_id):
            assert version_id == 31
            return {'version': version, 'batches': []}

    class StubImportBatchService:
        def parse_mapping_workbook(self, version_id, upload):
            assert version_id == 31
            assert upload.filename == 'registry-import.xlsx'
            return {
                'filename': 'registry-import.xlsx',
                'headers': ['Kode Program', 'Nama Program'],
                'sample_rows': [{'Kode Program': 'PRG-001', 'Nama Program': 'Program A'}],
                'fields': [{'key': 'record_code', 'label': 'Record Code', 'type': 'string', 'required': True}],
                'auto_mapping': {'record_code': 'Kode Program'},
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)
    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.post(
        '/data-registries/versions/31/import-mapping',
        data={'action': 'preview_mapping', 'excel_file': (Path('/dev/null').open('rb'), 'registry-import.xlsx')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Shell Mapping Import Registry' in html
    assert 'registry-import.xlsx' in html
    assert 'Kode Program' in html
    assert 'Record Code' in html
    assert 'Upload ulang file yang sama lalu simpan sebagai batch staging registry.' in html
    assert 'Pilihan mapping di atas akan dipakai saat batch disimpan.' in html
    assert 'name="mapping_record_code"' in html
    assert 'name="csrf_token"' in html


def test_data_registry_mapping_shell_create_batch_redirects_to_batch_console(monkeypatch):
    app = create_app('testing')

    version = SimpleNamespace(
        id=31,
        uuid='version-uuid',
        registry_id=10,
        version_number=2,
        status='draft',
        schema_json={'fields': [{'key': 'record_code', 'type': 'string', 'required': True, 'label': 'Record Code'}]},
        source_snapshot={'source_name': 'diskominfo-jabar'},
    )
    created = {}

    class StubVersionService:
        def get_version_detail(self, version_id):
            assert version_id == 31
            return {'version': version, 'batches': []}

    class StubImportBatchService:
        def create_batch_from_workbook(self, version_id, upload, mapping_config, actor=None):
            created['version_id'] = version_id
            created['filename'] = upload.filename
            created['mapping_config'] = mapping_config
            return {'batch': SimpleNamespace(id=101)}

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)
    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.post(
        '/data-registries/versions/31/import-mapping',
        data={
            'action': 'create_batch',
            'mapping_record_code': 'Kode Program',
            'excel_file': (Path('/dev/null').open('rb'), 'registry-import.xlsx'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/import-batches/101/import-console')
    assert created == {
        'version_id': 31,
        'filename': 'registry-import.xlsx',
        'mapping_config': {'record_code': 'Kode Program'},
    }


def test_data_registry_manual_entry_post_redirects_to_batch_console(monkeypatch):
    app = create_app('testing')

    created = {}
    version = SimpleNamespace(id=31, status='draft', schema_json={'fields': [{'key': 'record_key'}, {'key': 'record_code'}, {'key': 'label'}, {'key': 'parent_code'}, {'key': 'admin_level'}]})

    class StubVersionService:
        def get_version_detail(self, version_id):
            assert version_id == 31
            return {'version': version, 'batches': []}

    class StubImportBatchService:
        def extract_importable_fields(self, version_or_schema):
            return [
                {'key': 'record_key', 'label': 'Record Key', 'required': True},
                {'key': 'record_code', 'label': 'Record Code', 'required': True},
                {'key': 'label', 'label': 'Label', 'required': True},
                {'key': 'parent_code', 'label': 'Parent Code', 'required': False},
                {'key': 'admin_level', 'label': 'Admin Level', 'required': False},
            ]

        def create_manual_entry_batch(self, version_id, row_payload, actor=None):
            created['version_id'] = version_id
            created['row_payload'] = row_payload
            created['actor'] = actor
            return {'batch': SimpleNamespace(id=202)}

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)
    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryImportBatchService', StubImportBatchService)

    client = app.test_client()
    response = client.post(
        '/data-registries/versions/31/manual-entry',
        data={
            'record_key': 'program:prg-001',
            'record_code': 'PRG-001',
            'label': 'Program A',
            'parent_code': '',
            'admin_level': 'program',
        },
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/import-batches/202/import-console')
    assert created == {
        'version_id': 31,
        'row_payload': {
            'record_key': 'program:prg-001',
            'record_code': 'PRG-001',
            'label': 'Program A',
            'parent_code': '',
            'admin_level': 'program',
        },
        'actor': None,
    }


def test_data_registry_manual_entry_post_requires_csrf_when_enabled():
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True)

    client = app.test_client()
    response = client.post('/data-registries/versions/31/manual-entry', data={'record_code': 'PRG-001'})

    assert response.status_code == 400


def test_data_registry_import_console_template_contains_validate_and_materialize_controls():
    template_content = Path('app/templates/pages/data_registry/import_batch_console.html').read_text(encoding='utf-8')
    version_template_content = Path('app/templates/pages/data_registry/import_console.html').read_text(encoding='utf-8')
    mapping_template_content = Path('app/templates/pages/data_registry/import_mapping.html').read_text(encoding='utf-8')

    assert 'dataRegistryBatchValidateForm' in template_content
    assert 'dataRegistryBatchValidateBtn' in template_content
    assert 'dataRegistryBatchMaterializeForm' in template_content
    assert 'dataRegistryBatchMaterializeBtn' in template_content
    assert 'name="csrf_token"' in template_content
    assert 'Mode Operator Cepat' in template_content
    assert 'Review row → validasi batch → materialisasi registry.' in template_content
    assert 'Preview dibatasi 20 row pertama agar console tetap ringan dibaca.' in template_content
    assert 'dataRegistryDownloadErrorWorkbookBtn' in template_content
    assert 'Ringkasan Materialisasi Registry Version' in template_content
    assert 'Status Batch' in template_content
    assert 'Batch siap dimaterialisasi ulang dengan aman' in template_content
    assert 'Preview cepat row staging untuk memastikan hasil validasi dan materialisasi sudah konsisten.' in template_content
    assert 'Sticky Ringkasan Batch' in template_content
    assert 'Mapped Payload Terbaca' in template_content
    assert 'Validation Errors Terbaca' in template_content
    assert 'position-sticky top-0' in template_content
    assert 'Upload Batch Baru' in template_content
    assert 'Status Version' in version_template_content
    assert 'Flow Ringkas Import' in version_template_content
    assert 'Siapkan batch staging' in version_template_content
    assert 'Validasi row dan cek error/duplikat' in version_template_content
    assert 'Materialisasi batch untuk refresh registry version' in version_template_content
    assert 'Belum ada batch import untuk version ini. Upload/mapping berikutnya akan muncul di console ini.' in version_template_content
    assert 'duplikat perlu perhatian' in version_template_content
    assert 'Buka Shell Mapping' in version_template_content
    assert 'Entry Manual Cepat' in version_template_content
    assert 'Pakai ini kalau mau input 1 record dulu dari browser' in version_template_content
    assert 'Simpan Entry Manual ke Batch Staging' in version_template_content
    assert 'Shell Mapping Import Registry' in mapping_template_content
    assert 'Upload & Baca Kolom Sumber' in mapping_template_content
    assert 'name="csrf_token"' in mapping_template_content
