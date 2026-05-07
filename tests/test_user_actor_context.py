from pathlib import Path
from types import SimpleNamespace

from app import create_app
from app.core.access.actor_context import build_actor_context, normalize_actor_settings


def test_normalize_actor_settings_enriches_scope_from_code():
    settings = normalize_actor_settings(
        {
            'active_year': '2026',
            'scope': {
                'type': 'unit',
                'code': 'ki',
            },
        }
    )

    assert settings == {
        'active_year': 2026,
        'scope': {
            'type': 'unit',
            'code': 'ki',
            'name': 'Kekayaan Intelektual',
            'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            'parent_code': 'divisi-pelayanan-hukum',
        },
    }


def test_build_actor_context_falls_back_to_employee_scope_when_user_settings_empty():
    actor = SimpleNamespace(
        id=9,
        uuid='user-uuid',
        roles=['pegawai_unit'],
        permissions=['submission:create'],
        settings={'active_year': 2026},
        employee=SimpleNamespace(
            details={
                'scope': {
                    'type': 'unit',
                    'code': 'ahu',
                }
            }
        ),
    )

    context = build_actor_context(actor)

    assert context['user_id'] == 9
    assert context['roles'] == ['pegawai_unit']
    assert context['permissions'] == ['submission:create']
    assert context['active_year'] == 2026
    assert context['scope']['code'] == 'ahu'
    assert context['scope']['name'] == 'Administrasi Hukum Umum'
    assert context['scope']['path'] == ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ahu']


def test_user_create_route_passes_active_year_and_scope_settings(monkeypatch):
    app = create_app('testing')
    app.config['LOGIN_DISABLED'] = True
    client = app.test_client()
    captured = {}

    class StubUserService:
        def register(self, username, email, password, is_seeding=False, roles=None, permissions=None, active=True, settings=None):
            captured['username'] = username
            captured['email'] = email
            captured['roles'] = roles
            captured['permissions'] = permissions
            captured['active'] = active
            captured['settings'] = settings
            return SimpleNamespace(
                id=1,
                uuid='user-uuid',
                username=username,
                email=email,
                active=bool(active),
                roles=['pegawai_unit'],
                permissions=['submission:create'],
                settings=settings,
                email_verified_at=None,
                last_login=None,
            )

    monkeypatch.setattr('app.modules.user.routes_web.UserService', StubUserService)

    response = client.post(
        '/users/create',
        data={
            'username': '123456789012345678',
            'email': 'pegawai@example.com',
            'password': 'Password1!',
            'confirm_password': 'Password1!',
            'active': 'y',
            'roles': 'pegawai_unit',
            'permissions': 'submission:create',
            'active_year': '2026',
            'scope_type': 'unit',
            'scope_code': 'ki',
        },
    )

    assert response.status_code == 200
    assert captured['settings'] == {
        'active_year': 2026,
        'scope': {
            'type': 'unit',
            'code': 'ki',
            'name': 'Kekayaan Intelektual',
            'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            'parent_code': 'divisi-pelayanan-hukum',
        },
    }


def test_user_detail_route_includes_settings_and_actor_context(monkeypatch):
    app = create_app('testing')
    app.config['LOGIN_DISABLED'] = True
    client = app.test_client()

    user = SimpleNamespace(
        id=11,
        uuid='user-uuid',
        username='123456789012345678',
        email='pegawai@example.com',
        active=True,
        roles=['pegawai_unit'],
        permissions=['submission:create'],
        settings={'active_year': 2026, 'scope': {'type': 'unit', 'code': 'ki'}},
        email_verified_at=None,
        last_login=None,
        created_at=None,
        updated_at=None,
        employee=None,
    )

    class StubRepository:
        def get_by_id(self, user_id):
            assert user_id == 11
            return user

    class StubUserService:
        def __init__(self):
            self.repository = StubRepository()

    monkeypatch.setattr('app.modules.user.routes_web.UserService', StubUserService)

    response = client.get('/users/data/11')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['settings'] == {
        'active_year': 2026,
        'scope': {
            'type': 'unit',
            'code': 'ki',
            'name': 'Kekayaan Intelektual',
            'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            'parent_code': 'divisi-pelayanan-hukum',
        },
    }
    assert payload['actor_context']['scope']['code'] == 'ki'
    assert payload['actor_context']['active_year'] == 2026


def test_user_management_template_and_js_expose_abac_setting_inputs():
    template_content = Path('app/templates/pages/user/user_index.html').read_text(encoding='utf-8')
    js_content = Path('app/src/js/pages/users.js').read_text(encoding='utf-8')

    assert 'active_year' in template_content
    assert 'scope_type' in template_content
    assert 'scope_code' in template_content
    assert 'active_year' in js_content
    assert 'scope_type' in js_content
    assert 'scope_code' in js_content
