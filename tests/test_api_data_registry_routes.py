from types import SimpleNamespace

import pytest

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def make_registry(**overrides):
    defaults = {
        'id': 10,
        'uuid': 'registry-uuid',
        'registry_slug': 'wilayah.administratif',
        'registry_code': 'WILAYAH-ADM',
        'name': 'Wilayah Administratif',
        'description': None,
        'registry_type': 'geo',
        'category_key': 'wilayah',
        'source_mode': 'import_file',
        'data_shape': 'hierarchical_geo',
        'is_year_scoped': False,
        'status': 'published',
        'schema_meta': {},
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_version(**overrides):
    defaults = {
        'id': 30,
        'uuid': 'registry-version-uuid',
        'registry_id': 10,
        'version_number': 3,
        'status': 'published',
        'schema_json': {'fields': [{'key': 'kode_wilayah'}]},
        'mapping_spec': {},
        'source_snapshot': {},
        'publish_notes': None,
        'published_at': None,
        'source_watermark': None,
        'materialized_watermark': None,
        'freshness_status': 'fresh',
        'freshness_signature': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def assert_validation_error(response, expected_message):
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert expected_message in payload['message']
    assert payload['data']['error_type'] == 'validation_error'


def test_data_registry_resource_api_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/api/v1/registry-resources/<string:registry_slug>/options',
        '/api/v1/registry-resources/<string:registry_slug>/lookup',
        '/api/v1/registry-resources/<string:registry_slug>/children',
        '/api/v1/registry-resources/<string:registry_slug>/tree',
        '/api/v1/registry-resources/<string:registry_slug>/feature-collection',
    ]

    for route in expected_routes:
        assert route in rules



def test_options_endpoint_returns_option_items(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubQueryService:
        def get_option_list(self, registry_slug, **kwargs):
            assert registry_slug == 'wilayah.administratif'
            return {
                'registry': make_registry(),
                'version': make_version(),
                'items': [
                    {
                        'label': 'Kabupaten Bandung',
                        'value': '3204',
                        'meta': {'record_key': 'city:3204', 'admin_level': 'city_regency'},
                    }
                ],
            }

    monkeypatch.setattr('app.api.v1.data_registries.routes.DataRegistryQueryService', StubQueryService)

    response = client.get('/api/v1/registry-resources/wilayah.administratif/options?admin_level=city_regency&parent_code=32')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['items'][0]['value'] == '3204'
    assert payload['data']['version']['version_number'] == 3



def test_lookup_endpoint_returns_record_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubQueryService:
        def get_lookup(self, registry_slug, **kwargs):
            assert registry_slug == 'wilayah.administratif'
            return {
                'registry': make_registry(),
                'version': make_version(),
                'record': {
                    'id': 2,
                    'record_key': 'city:3204',
                    'record_code': '3204',
                    'label': 'Kabupaten Bandung',
                    'display_label': 'Kabupaten Bandung',
                    'admin_level': 'city_regency',
                    'parent_record_id': 1,
                    'centroid': None,
                    'payload': {},
                },
            }

    monkeypatch.setattr('app.api.v1.data_registries.routes.DataRegistryQueryService', StubQueryService)

    response = client.get('/api/v1/registry-resources/wilayah.administratif/lookup?record_code=3204')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['record']['record_code'] == '3204'



def test_children_endpoint_returns_items(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubQueryService:
        def get_children(self, registry_slug, **kwargs):
            assert registry_slug == 'wilayah.administratif'
            return {
                'registry': make_registry(),
                'version': make_version(),
                'items': [
                    {'id': 3, 'record_code': '3273', 'label': 'Kota Bandung', 'admin_level': 'city_regency', 'children': []},
                    {'id': 2, 'record_code': '3204', 'label': 'Kabupaten Bandung', 'admin_level': 'city_regency', 'children': []},
                ],
            }

    monkeypatch.setattr('app.api.v1.data_registries.routes.DataRegistryQueryService', StubQueryService)

    response = client.get('/api/v1/registry-resources/wilayah.administratif/children?parent_code=32&admin_level=city_regency')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert [item['record_code'] for item in payload['data']['items']] == ['3273', '3204']



def test_tree_endpoint_returns_nested_items(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubQueryService:
        def get_tree(self, registry_slug, **kwargs):
            assert registry_slug == 'wilayah.administratif'
            return {
                'registry': make_registry(),
                'version': make_version(),
                'items': [
                    {
                        'id': 1,
                        'record_code': '32',
                        'label': 'Jawa Barat',
                        'admin_level': 'province',
                        'children': [
                            {
                                'id': 2,
                                'record_code': '3204',
                                'label': 'Kabupaten Bandung',
                                'admin_level': 'city_regency',
                                'children': [],
                            }
                        ],
                    }
                ],
            }

    monkeypatch.setattr('app.api.v1.data_registries.routes.DataRegistryQueryService', StubQueryService)

    response = client.get('/api/v1/registry-resources/wilayah.administratif/tree?root_level=province&max_depth=2')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['items'][0]['children'][0]['record_code'] == '3204'



def test_feature_collection_endpoint_returns_geojson(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubQueryService:
        def get_feature_collection(self, registry_slug, **kwargs):
            assert registry_slug == 'wilayah.administratif'
            return {
                'type': 'FeatureCollection',
                'features': [
                    {
                        'type': 'Feature',
                        'geometry': {'type': 'Point', 'coordinates': [107.60981, -6.914744]},
                        'properties': {'record_code': '3204', 'label': 'Kabupaten Bandung'},
                    }
                ],
            }

    monkeypatch.setattr('app.api.v1.data_registries.routes.DataRegistryQueryService', StubQueryService)

    response = client.get('/api/v1/registry-resources/wilayah.administratif/feature-collection')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['feature_collection']['type'] == 'FeatureCollection'
    assert payload['data']['feature_collection']['features'][0]['properties']['record_code'] == '3204'



def test_options_endpoint_returns_authorization_error_when_service_denies(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubQueryService:
        def get_option_list(self, registry_slug, **kwargs):
            raise PermissionError('Actor tidak memiliki izin membaca registry resource ini.')

    monkeypatch.setattr('app.api.v1.data_registries.routes.DataRegistryQueryService', StubQueryService)

    response = client.get('/api/v1/registry-resources/wilayah.administratif/options')

    assert response.status_code == 403
    payload = response.get_json()
    assert payload['success'] is False
    assert payload['data']['error_type'] == 'authorization_error'
    assert 'izin membaca registry resource' in payload['message']


@pytest.mark.parametrize(
    'endpoint,patch_target,service_method,expected_message',
    [
        (
            '/api/v1/registry-resources/wilayah.administratif/options',
            'app.api.v1.data_registries.routes.DataRegistryQueryService',
            'get_option_list',
            'Published version registry tidak ditemukan.',
        ),
        (
            '/api/v1/registry-resources/wilayah.administratif/lookup',
            'app.api.v1.data_registries.routes.DataRegistryQueryService',
            'get_lookup',
            'record_key atau record_code wajib diisi.',
        ),
        (
            '/api/v1/registry-resources/wilayah.administratif/children',
            'app.api.v1.data_registries.routes.DataRegistryQueryService',
            'get_children',
            'parent_record_id atau parent_code wajib diisi.',
        ),
        (
            '/api/v1/registry-resources/wilayah.administratif/tree',
            'app.api.v1.data_registries.routes.DataRegistryQueryService',
            'get_tree',
            'max_depth minimal 1.',
        ),
        (
            '/api/v1/registry-resources/wilayah.administratif/feature-collection',
            'app.api.v1.data_registries.routes.DataRegistryQueryService',
            'get_feature_collection',
            'Published version registry tidak ditemukan.',
        ),
    ],
)
def test_data_registry_resource_api_validation_errors_return_standard_400(
    monkeypatch,
    endpoint,
    patch_target,
    service_method,
    expected_message,
):
    app = create_app('testing')
    client = app.test_client()

    class StubService:
        pass

    def raise_validation_error(*args, **kwargs):
        raise ValueError(expected_message)

    setattr(StubService, service_method, raise_validation_error)
    monkeypatch.setattr(patch_target, StubService)

    response = client.get(endpoint)

    assert_validation_error(response, expected_message)
