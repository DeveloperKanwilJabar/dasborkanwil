from types import SimpleNamespace

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def test_data_registry_web_registry_shell_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/data-registries',
        '/data-registries/create',
        '/data-registries/<int:registry_id>',
        '/data-registries/<int:registry_id>/records',
        '/data-registries/records/<int:record_id>/update',
        '/data-registries/records/<int:record_id>/toggle-active',
    ]

    for route in expected_routes:
        assert route in rules


def test_data_registry_index_page_returns_browser_ready_registry_list(monkeypatch):
    app = create_app('testing')
    registries = [
        SimpleNamespace(
            id=10,
            uuid='registry-uuid',
            registry_slug='master.program',
            registry_code='MASTER-PROGRAM',
            name='Master Program',
            description='Bank data program prioritas.',
            registry_type='master_data',
            category_key='master_data',
            source_mode='import_file',
            data_shape='hierarchical',
            is_year_scoped=False,
            status='draft',
        )
    ]
    draft_version = SimpleNamespace(id=31, version_number=1, status='draft')

    class StubRegistryRepository:
        def get_all(self):
            return registries

    class StubRegistryService:
        def __init__(self):
            self.repository = StubRegistryRepository()

    class StubVersionRepository:
        def get_draft_version(self, registry_id):
            assert registry_id == 10
            return draft_version

        def get_published_version(self, registry_id):
            assert registry_id == 10
            return None

    class StubVersionService:
        def __init__(self):
            self.repository = StubVersionRepository()

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)
    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryVersionService', StubVersionService)

    client = app.test_client()
    response = client.get('/data-registries')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Data Registry / Master Data' in html
    assert 'Buat Data Registry' in html
    assert 'Master Program' in html
    assert 'master.program' in html
    assert 'MASTER-PROGRAM' in html
    assert 'Draft v1 siap dipakai untuk import console.' in html
    assert '/data-registries/versions/31/import-console' in html
    assert '/data-registries/10' in html
    assert 'Buka Workspace Registry' in html


def test_data_registry_detail_page_returns_manual_input_workspace(monkeypatch):
    app = create_app('testing')

    registry = SimpleNamespace(
        id=10,
        uuid='registry-uuid',
        registry_slug='master.program',
        registry_code='MASTER-PROGRAM',
        name='Master Program',
        description='Bank data program prioritas.',
        registry_type='master_data',
        category_key='master_data',
        source_mode='import_file',
        data_shape='hierarchical',
        status='draft',
    )
    draft_version = SimpleNamespace(
        id=31,
        version_number=2,
        status='draft',
        freshness_status='stale',
        materialized_at='2026-05-26T10:15:00+00:00',
        materialization_metadata={'record_count': 2},
    )
    published_version = SimpleNamespace(
        id=30,
        version_number=1,
        status='published',
    )
    manual_entry_fields = [
        {'key': 'record_key', 'label': 'Record Key', 'required': True, 'type': 'text', 'options': []},
        {'key': 'record_code', 'label': 'Record Code', 'required': True, 'type': 'select', 'options': ['aktif', 'nonaktif']},
        {'key': 'label', 'label': 'Label', 'required': True, 'type': 'text', 'options': []},
    ]
    recent_batches = [
        SimpleNamespace(id=88, original_filename='manual-entry-v31.xlsx', status='mapped', total_rows=1),
    ]
    records = [
        SimpleNamespace(
            id=501,
            record_key='status-aktif',
            record_code='aktif',
            label='Status Aktif',
            admin_level='master_data',
            parent_record_id=None,
            is_active=True,
            payload={'record_code': 'aktif', 'label': 'Status Aktif'},
        ),
        SimpleNamespace(
            id=502,
            record_key='status-nonaktif',
            record_code='nonaktif',
            label='Status Nonaktif',
            admin_level='master_data',
            parent_record_id=None,
            is_active=False,
            payload={'record_code': 'nonaktif', 'label': 'Status Nonaktif'},
        ),
    ]

    class StubRegistryService:
        def get_registry_workspace(self, registry_id, record_limit=20):
            assert registry_id == 10
            assert record_limit == 20
            return {
                'registry': registry,
                'draft_version': draft_version,
                'published_version': published_version,
                'manual_entry_version': draft_version,
                'manual_entry_fields': manual_entry_fields,
                'record_preview_version': draft_version,
                'records': records,
                'record_count': 2,
                'recent_batches': recent_batches,
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)

    client = app.test_client()
    response = client.get('/data-registries/10')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Workspace Data Registry' in html
    assert 'Master Program' in html
    assert 'Input Manual Cepat' in html
    assert 'name="record_key"' in html
    assert 'name="record_code"' in html
    assert 'Pilih Record Code' in html
    assert 'aktif' in html
    assert 'nonaktif' in html
    assert 'Kirim ke Batch Staging' in html
    assert '/data-registries/versions/31/manual-entry' in html
    assert '/data-registries/versions/31/import-console' in html
    assert '/data-registries/10/records' in html
    assert 'Preview Record Tersimpan' in html
    assert 'Status Aktif' in html
    assert 'Status Nonaktif' in html
    assert 'manual-entry-v31.xlsx' in html
    assert '2 record' in html


def test_data_registry_record_list_page_returns_materialized_entries(monkeypatch):
    app = create_app('testing')

    registry = SimpleNamespace(
        id=10,
        registry_slug='master.program',
        registry_code='MASTER-PROGRAM',
        name='Master Program',
        description='Bank data program prioritas.',
        status='draft',
    )
    draft_version = SimpleNamespace(id=31, version_number=2, status='draft')
    record_columns = [
        {'key': 'record_code', 'label': 'Kode Record', 'source': 'system'},
        {'key': 'label', 'label': 'Nama Program', 'source': 'system'},
        {'key': 'tipe', 'label': 'Tipe', 'source': 'payload'},
        {'key': 'jenis', 'label': 'Jenis', 'source': 'payload'},
    ]
    record_rows = [
        {
            'id': 501,
            'record_key': 'master_data:A1',
            'record_code': 'A1',
            'label': 'Program A1',
            'admin_level': 'master_data',
            'parent_record_id': None,
            'is_active': True,
            'updated_at': '2026-06-01T11:00:00+00:00',
            'payload': {'kode': 'A1', 'tipe': 'D', 'jenis': 'A'},
            'column_values': {'record_code': 'A1', 'label': 'Program A1', 'tipe': 'D', 'jenis': 'A'},
        },
        {
            'id': 502,
            'record_key': 'master_data:B2',
            'record_code': 'B2',
            'label': 'Program B2',
            'admin_level': 'master_data',
            'parent_record_id': None,
            'is_active': False,
            'updated_at': '2026-06-01T11:10:00+00:00',
            'payload': {'kode': 'B2', 'tipe': 'E', 'jenis': 'B'},
            'column_values': {'record_code': 'B2', 'label': 'Program B2', 'tipe': 'E', 'jenis': 'B'},
        },
    ]
    edit_fields = [
        {'key': 'record_code', 'label': 'Kode Record', 'type': 'text', 'required': True, 'readonly': False, 'options': []},
        {'key': 'label', 'label': 'Nama Program', 'type': 'text', 'required': True, 'readonly': False, 'options': []},
        {'key': 'tipe', 'label': 'Tipe', 'type': 'select', 'required': False, 'readonly': False, 'options': ['D', 'E']},
        {'key': 'jenis', 'label': 'Jenis', 'type': 'text', 'required': False, 'readonly': False, 'options': []},
    ]

    class StubRegistryService:
        def get_registry_record_list(self, registry_id, record_limit=100):
            assert registry_id == 10
            assert record_limit == 100
            return {
                'registry': registry,
                'draft_version': draft_version,
                'published_version': None,
                'record_list_version': draft_version,
                'records': [],
                'record_count': 2,
                'record_columns': record_columns,
                'record_rows': record_rows,
                'edit_fields': edit_fields,
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)

    client = app.test_client()
    response = client.get('/data-registries/10/records')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Daftar Record Registry' in html
    assert 'Master Program' in html
    assert '/static/libs/gridjs/dist/theme/mermaid.min.css' in html
    assert '/static/libs/gridjs/dist/gridjs.umd.js' in html
    assert '/static/js/pages/data-registry-records.js' in html
    assert 'id="registry-records-grid"' in html
    assert 'id="recordStatusFilter"' in html
    assert 'id="recordLevelFilter"' in html
    assert 'id="recordEditModal"' in html
    assert 'Kode Record' in html
    assert 'Nama Program' in html
    assert 'Tipe' in html
    assert 'Jenis' in html
    assert 'Program A1' in html
    assert 'Program B2' in html
    assert 'master_data:A1' in html
    assert 'master_data:B2' in html
    assert 'A1' in html
    assert 'B2' in html
    assert 'recordRowsData' in html
    assert '/data-registries/records/0/update' in html
    assert '/data-registries/records/0/toggle-active' in html
    assert 'aktif' in html
    assert 'nonaktif' in html
    assert '2 record' in html
    assert '/data-registries/10' in html


def test_data_registry_record_update_post_redirects_back_to_list(monkeypatch):
    app = create_app('testing')
    captured = {}

    class StubRegistryService:
        def update_registry_record(self, record_id, data, actor=None):
            captured['record_id'] = record_id
            captured['data'] = data
            captured['actor'] = actor
            return {
                'record': SimpleNamespace(id=501, registry_id=10, label='Program A1 Revisi'),
                'registry': SimpleNamespace(id=10),
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)

    client = app.test_client()
    response = client.post(
        '/data-registries/records/501/update',
        data={
            'registry_id': '10',
            'record_code': 'A1',
            'label': 'Program A1 Revisi',
            'tipe': 'D',
            'jenis': 'A+',
        },
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/10/records')
    assert captured['record_id'] == 501
    assert captured['data']['registry_id'] == '10'
    assert captured['data']['record_code'] == 'A1'
    assert captured['data']['label'] == 'Program A1 Revisi'
    assert captured['data']['tipe'] == 'D'
    assert captured['data']['jenis'] == 'A+'


def test_data_registry_record_toggle_active_post_redirects_back_to_list(monkeypatch):
    app = create_app('testing')
    captured = {}

    class StubRegistryService:
        def set_registry_record_active(self, record_id, is_active, registry_id=None, actor=None):
            captured['record_id'] = record_id
            captured['is_active'] = is_active
            captured['registry_id'] = registry_id
            captured['actor'] = actor
            return {
                'record': SimpleNamespace(id=501, registry_id=10, is_active=False),
                'registry': SimpleNamespace(id=10),
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)

    client = app.test_client()
    response = client.post(
        '/data-registries/records/501/toggle-active',
        data={
            'registry_id': '10',
            'is_active': 'false',
        },
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/10/records')
    assert captured['record_id'] == 501
    assert captured['registry_id'] == 10
    assert captured['is_active'] is False


def test_data_registry_create_page_returns_browser_ready_form():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/data-registries/create')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Buat Data Registry' in html
    assert 'id="dataRegistryCreateForm"' in html
    assert 'name="name"' in html
    assert 'name="registry_slug"' in html
    assert 'name="registry_code"' in html
    assert 'name="template_key"' in html
    assert 'name="csrf_token"' in html
    assert 'master_data_hierarkis' in html
    assert 'wilayah_administratif' in html
    assert 'Draft version awal akan dibuat otomatis' in html
    assert 'entry manual 1 record' in html
    assert 'upload Excel sebagai batch staging' in html
    assert 'Mekanisme Data Registry' in html
    assert 'Referensi kolom starter' in html
    assert 'schema_json.fields' in html


def test_data_registry_create_post_requires_csrf_when_enabled():
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True)

    client = app.test_client()
    response = client.post(
        '/data-registries/create',
        data={
            'name': 'Master Program',
            'registry_slug': 'master.program',
            'template_key': 'master_data_hierarkis',
        },
    )

    assert response.status_code == 400


def test_data_registry_create_post_redirects_to_import_console(monkeypatch):
    app = create_app('testing')
    captured = {}

    class StubRegistryService:
        def create_registry(self, data, actor=None):
            captured['data'] = data
            captured['actor'] = actor
            return {
                'registry': SimpleNamespace(id=10, registry_slug='master.program'),
                'draft_version': SimpleNamespace(id=31, registry_id=10, version_number=1, status='draft'),
            }

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)

    client = app.test_client()
    response = client.post(
        '/data-registries/create',
        data={
            'name': 'Master Program',
            'registry_slug': 'master.program',
            'registry_code': 'MASTER-PROGRAM',
            'description': 'Bank data program prioritas.',
            'template_key': 'master_data_hierarkis',
            'is_year_scoped': '1',
        },
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/data-registries/versions/31/import-console')
    assert captured['data']['name'] == 'Master Program'
    assert captured['data']['registry_slug'] == 'master.program'
    assert captured['data']['registry_code'] == 'MASTER-PROGRAM'
    assert captured['data']['registry_type'] == 'master_data'
    assert captured['data']['category_key'] == 'master_data'
    assert captured['data']['source_mode'] == 'import_file'
    assert captured['data']['data_shape'] == 'hierarchical'
    assert captured['data']['is_year_scoped'] is True
    assert captured['data']['mapping_spec']['materialization_contract'] == 'generic_v1'
    assert captured['data']['schema_json']['fields'][0]['key'] == 'record_key'
    assert captured['data']['schema_meta']['starter_template'] == 'master_data_hierarkis'


def test_data_registry_create_post_rerenders_form_on_validation_error(monkeypatch):
    app = create_app('testing')

    class StubRegistryService:
        def create_registry(self, data, actor=None):
            raise ValueError('Registry slug sudah digunakan.')

    monkeypatch.setattr('app.modules.data_registry.routes_web.DataRegistryService', StubRegistryService)

    client = app.test_client()
    response = client.post(
        '/data-registries/create',
        data={
            'name': 'Master Program',
            'registry_slug': 'master.program',
            'registry_code': 'MASTER-PROGRAM',
            'description': 'Bank data program prioritas.',
            'template_key': 'master_data_hierarkis',
            'is_year_scoped': '1',
        },
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Registry slug sudah digunakan.' in html
    assert 'value="Master Program"' in html
    assert 'value="master.program"' in html
    assert 'value="MASTER-PROGRAM"' in html
    assert 'Bank data program prioritas.' in html
