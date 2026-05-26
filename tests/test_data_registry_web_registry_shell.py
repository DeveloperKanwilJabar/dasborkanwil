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
