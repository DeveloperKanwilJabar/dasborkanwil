from argparse import Namespace
from types import SimpleNamespace

from app.core.access import enrich_scope
from seeder import (
    DEFAULT_MATRIX_TEST_PASSWORD,
    DEFAULT_WILAYAH_REGISTRY_CSV_PATH,
    DEFAULT_WILAYAH_REGISTRY_SLUG,
    build_matrix_fixture_payload,
    build_wilayah_registry_fixture_payload,
    run_selected_seed_profiles,
    seed_matrix_test_fixture,
    seed_wilayah_registry,
)


class StubUserRepository:
    def __init__(self, existing=None):
        self.existing = existing or {}
        self.saved = []

    def find_one_by(self, **filters):
        username = filters.get('username')
        return self.existing.get(username)

    def save(self, user):
        self.saved.append(user)
        self.existing[user.username] = user
        return user


class StubUserService:
    def __init__(self):
        self.register_calls = []

    def register(self, **kwargs):
        self.register_calls.append(kwargs)
        return SimpleNamespace(
            id=len(self.register_calls),
            uuid=f"user-uuid-{len(self.register_calls)}",
            username=kwargs['username'],
            email=kwargs['email'],
            roles=kwargs['roles'],
            permissions=kwargs['permissions'],
            settings=kwargs['settings'],
            active=kwargs.get('active', True),
        )


class StubFormRepository:
    def __init__(self, existing=None):
        self.existing = existing or {}

    def find_one_by(self, **filters):
        code = filters.get('code')
        return self.existing.get(code)


class StubFormService:
    def __init__(self, form_repository=None):
        self.repository = form_repository or StubFormRepository()
        self.create_calls = []
        self.update_calls = []

    def create_form(self, data, actor=None):
        self.create_calls.append({'data': data, 'actor': actor})
        form = SimpleNamespace(
            id=len(self.create_calls),
            code=data['code'],
            slug=data['slug'],
            name=data['name'],
        )
        self.repository.existing[data['code']] = form
        return {
            'form': form,
            'draft_version': SimpleNamespace(id=100 + len(self.create_calls), form_id=form.id),
        }

    def update_form_identity(self, form_id, data, actor=None):
        self.update_calls.append({'form_id': form_id, 'data': data, 'actor': actor})
        existing = next(item for item in self.repository.existing.values() if item.id == form_id)
        existing.code = data['code']
        existing.slug = data['slug']
        existing.name = data['name']
        return existing


class StubFormVersionService:
    def __init__(self):
        self.create_calls = []
        self.publish_calls = []

    def create_draft_version(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            id=200 + len(self.create_calls),
            form_id=kwargs['form_id'],
            schema=kwargs['schema'],
            status='draft',
            is_published=False,
        )

    def publish_version(self, version_id, actor=None):
        self.publish_calls.append({'version_id': version_id, 'actor': actor})
        return SimpleNamespace(id=version_id, status='published', is_published=True)


class StubRegistryRepository:
    def __init__(self, registry=None):
        self.registry = registry
        self.saved = []

    def get_by_slug(self, slug):
        if self.registry and self.registry.registry_slug == slug:
            return self.registry
        return None

    def save(self, registry):
        self.registry = registry
        self.saved.append(registry)
        return registry


class StubRegistryVersionRepository:
    def __init__(self, published_version=None, draft_version=None):
        self.published_version = published_version
        self.draft_version = draft_version
        self.saved = []

    def get_published_version(self, registry_id):
        return self.published_version

    def get_draft_version(self, registry_id):
        return self.draft_version

    def save(self, version):
        self.draft_version = version
        self.saved.append(version)
        return version


class StubDataRegistryService:
    def __init__(self):
        self.create_calls = []
        self.publish_calls = []

    def create_registry(self, data, actor=None):
        self.create_calls.append({'data': data, 'actor': actor})
        registry = SimpleNamespace(id=10, registry_slug=data['registry_slug'])
        draft_version = SimpleNamespace(id=20, registry_id=10, status='draft')
        return {'registry': registry, 'draft_version': draft_version}

    def publish_registry(self, registry_id, version_id=None, actor=None):
        self.publish_calls.append({'registry_id': registry_id, 'version_id': version_id, 'actor': actor})
        return {'published_version': SimpleNamespace(id=version_id, status='published')}


class StubDataRegistryVersionService:
    def __init__(self):
        self.create_calls = []

    def create_draft_version(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(id=30, registry_id=kwargs['registry_id'], status='draft')


class StubMaterializationService:
    def __init__(self):
        self.calls = []

    def materialize_wilayah_rows(self, registry_version_id, source_rows, actor=None):
        rows = list(source_rows)
        self.calls.append({'registry_version_id': registry_version_id, 'source_rows': rows, 'actor': actor})
        return {
            'record_count': 4,
            'source_row_count': len(rows),
        }


def test_build_matrix_fixture_payload_contains_expected_users_and_forms():
    payload = build_matrix_fixture_payload()

    assert payload['password'] == DEFAULT_MATRIX_TEST_PASSWORD
    assert [user['key'] for user in payload['users']] == [
        'admin_kanwil',
        'pegawai_ki',
        'pegawai_ahu',
        'kadiv_yankum',
    ]
    assert [form['code'] for form in payload['forms']] == [
        'MTRX-F1-KI',
        'MTRX-F2-AHU',
        'MTRX-F3-DIVPH',
    ]

    admin = payload['users'][0]
    assert admin['roles'] == ['admin_lintas_bagian']
    assert admin['settings']['scope'] == enrich_scope({'type': 'kanwil', 'code': 'kanwil-jabar'})

    form_f3 = payload['forms'][2]
    assert form_f3['target_scope'] == enrich_scope({'type': 'division', 'code': 'divisi-pelayanan-hukum'})
    assert form_f3['access_policy_key'] == 'form.division_broadcast'
    assert form_f3['schema']['components'][0]['key'] == 'judul_kegiatan'


def test_seed_matrix_test_fixture_registers_users_and_publishes_forms():
    user_service = StubUserService()
    user_repository = StubUserRepository()
    form_repository = StubFormRepository()
    form_service = StubFormService(form_repository=form_repository)
    version_service = StubFormVersionService()

    result = seed_matrix_test_fixture(
        password='Rahasia#2026',
        user_service=user_service,
        user_repository=user_repository,
        form_service=form_service,
        form_repository=form_repository,
        form_version_service=version_service,
    )

    assert len(user_service.register_calls) == 4
    assert len(form_service.create_calls) == 3
    assert len(version_service.publish_calls) == 3
    assert result['password'] == 'Rahasia#2026'
    assert result['users'][1]['username'] == '555555555555555555'
    assert result['forms'][0]['target_scope_code'] == 'ki'
    assert result['forms'][2]['published_version_id'] == 203


def test_seed_matrix_test_fixture_updates_existing_user_and_form_when_reseeded():
    existing_user = SimpleNamespace(
        id=10,
        uuid='existing-user-uuid',
        username='888888888888888888',
        email='old-admin@example.com',
        roles=['pegawai_unit'],
        permissions=[],
        settings={},
        active=False,
        set_password=lambda password: setattr(existing_user, 'password', password),
    )
    existing_form = SimpleNamespace(
        id=99,
        code='MTRX-F1-KI',
        slug='old-slug',
        name='Old Form',
    )

    user_service = StubUserService()
    user_repository = StubUserRepository(existing={existing_user.username: existing_user})
    form_repository = StubFormRepository(existing={existing_form.code: existing_form})
    form_service = StubFormService(form_repository=form_repository)
    version_service = StubFormVersionService()

    result = seed_matrix_test_fixture(
        user_service=user_service,
        user_repository=user_repository,
        form_service=form_service,
        form_repository=form_repository,
        form_version_service=version_service,
    )

    assert len(user_service.register_calls) == 3
    assert user_repository.saved[0].email == 'agen.admin@kemenkum.go.id'
    assert user_repository.saved[0].roles == ['admin_lintas_bagian']
    assert len(form_service.create_calls) == 2
    assert form_service.update_calls[0]['form_id'] == 99
    assert result['forms'][0]['form_id'] == 99
    assert len(version_service.publish_calls) == 3


def test_build_wilayah_registry_fixture_payload_uses_canonical_slug_and_csv_default():
    payload = build_wilayah_registry_fixture_payload()

    assert payload['registry_slug'] == DEFAULT_WILAYAH_REGISTRY_SLUG
    assert payload['csv_path'] == DEFAULT_WILAYAH_REGISTRY_CSV_PATH
    assert payload['mapping_spec']['source_format'] == 'csv'
    assert payload['schema_json']['fields'][0]['key'] == 'record_code'


def test_seed_wilayah_registry_bootstraps_registry_from_csv(tmp_path):
    csv_path = tmp_path / 'wilayah.csv'
    csv_path.write_text(
        'id,kemendagri_provinsi_kode,kemendagri_kota_kode,kemendagri_kecamatan_kode,kemendagri_kelurahan_kode,kemendagri_provinsi_nama,kemendagri_kota_nama,kemendagri_kecamatan_nama,kemendagri_kelurahan_nama,bps_provinsi_kode,bps_kota_kode,bps_kecamatan_kode,bps_kelurahan_kode,bps_provinsi_nama,bps_kota_nama,bps_kecamatan_nama,bps_kelurahan_nama,latitude,longitude,kode_pos,status_adm\n'
        '1,32,32.01,32.01.01,32.01.01.1001,JAWA BARAT,KAB. BOGOR,CIBINONG,HARAPANJAYA,32.0,3201.0,3201010.0,3201010001.0,JAWA BARAT,KABUPATEN BOGOR,CIBINONG,HARAPAN JAYA,-6.485088,106.854729,16913.0,\n',
        encoding='utf-8',
    )

    registry_service = StubDataRegistryService()
    registry_repository = StubRegistryRepository()
    version_service = StubDataRegistryVersionService()
    version_repository = StubRegistryVersionRepository()
    materialization_service = StubMaterializationService()

    result = seed_wilayah_registry(
        csv_path=str(csv_path),
        registry_service=registry_service,
        registry_repository=registry_repository,
        version_service=version_service,
        version_repository=version_repository,
        materialization_service=materialization_service,
    )

    assert registry_service.create_calls[0]['data']['registry_slug'] == DEFAULT_WILAYAH_REGISTRY_SLUG
    assert materialization_service.calls[0]['registry_version_id'] == 20
    assert materialization_service.calls[0]['source_rows'][0]['kemendagri_kelurahan_kode'] == '32.01.01.1001'
    assert registry_service.publish_calls[0]['version_id'] == 20
    assert result['record_count'] == 4
    assert result['source_row_count'] == 1


def test_run_selected_seed_profiles_dispatches_wilayah_registry(monkeypatch):
    calls = []

    monkeypatch.setattr(
        'seeder.seed_wilayah_registry',
        lambda csv_path: calls.append(('seed', csv_path)) or {
            'registry': SimpleNamespace(registry_slug=DEFAULT_WILAYAH_REGISTRY_SLUG),
            'published_version': SimpleNamespace(id=77),
            'record_count': 4,
            'source_row_count': 1,
            'csv_path': csv_path,
        },
    )
    monkeypatch.setattr('seeder.print_wilayah_registry_summary', lambda result: calls.append(('print', result['csv_path'])))

    run_selected_seed_profiles(
        Namespace(
            profile=['wilayah_registry'],
            matrix_password='ignored',
            wilayah_csv='instance/custom.csv',
        )
    )

    assert calls == [
        ('seed', 'instance/custom.csv'),
        ('print', 'instance/custom.csv'),
    ]
