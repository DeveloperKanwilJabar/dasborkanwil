from types import SimpleNamespace

from app.core.access import enrich_scope
from seeder import DEFAULT_MATRIX_TEST_PASSWORD, build_matrix_fixture_payload, seed_matrix_test_fixture


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
