import argparse
import csv
import os

from dotenv import load_dotenv

from app.core.access import enrich_scope
from app.modules.employee.services import EmployeeService
from app.modules.form.repositories import FormRepository
from app.modules.form.services import FormService, FormVersionService
from app.modules.user.repositories import UserRepository
from app.modules.user.services import UserService

load_dotenv()

DEFAULT_MATRIX_TEST_PASSWORD = 'MatrixTest#2026'


def seed_employees():
    """Seed data pegawai dari CSV."""
    file_path = 'instance/pegawai.csv'
    emp_service = EmployeeService()

    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            try:
                emp_service.add(
                    nip=row['nip'],
                    name=row['full_name'],
                    unit=row['unit'],
                    skip_if_exists=True,
                )
                print(f"✅ Pegawai OK: {row['nip']}")
            except ValueError as error:
                print(f"❌ Error seed pegawai {row.get('nip')}: {str(error)}")
    print('✅ Seeding data pegawai selesai.')


def seed_user_agents():
    """Seed data user Agentic AI."""
    user = _upsert_user(
        {
            'key': 'agentic_ai',
            'username': '999999999999999999',
            'email': 'agent.super@kemenkum.go.id',
            'password': 'JalanJakarta#27',
            'roles': ['superadmin'],
            'permissions': [],
            'settings': {'active_year': 2026},
            'active': True,
        }
    )
    print(f'✅ Seeding data agen selesai: {user.username}')
    return user


def build_matrix_fixture_payload(password=DEFAULT_MATRIX_TEST_PASSWORD):
    admin_scope = enrich_scope({'type': 'kanwil', 'code': 'kanwil-jabar'})
    unit_ki_scope = enrich_scope({'type': 'unit', 'code': 'ki'})
    unit_ahu_scope = enrich_scope({'type': 'unit', 'code': 'ahu'})
    division_scope = enrich_scope({'type': 'division', 'code': 'divisi-pelayanan-hukum'})

    users = [
        {
            'key': 'admin_kanwil',
            'label': 'Admin Kanwil',
            'username': '888888888888888888',
            'email': 'agen.admin@kemenkum.go.id',
            'password': password,
            'roles': ['admin_lintas_bagian'],
            'permissions': [],
            'settings': {
                'active_year': 2026,
                'scope': admin_scope,
            },
            'active': True,
        },
        {
            'key': 'pegawai_ki',
            'label': 'Pegawai Unit KI',
            'username': '555555555555555555',
            'email': 'agen.ki@kemenkum.go.id',
            'password': password,
            'roles': ['pegawai_unit'],
            'permissions': ['submission:create'],
            'settings': {
                'active_year': 2026,
                'scope': unit_ki_scope,
            },
            'active': True,
        },
        {
            'key': 'pegawai_ahu',
            'label': 'Pegawai Unit AHU',
            'username': '666666666666666666',
            'email': 'agen.ahu@kemenkum.go.id',
            'password': password,
            'roles': ['pegawai_unit'],
            'permissions': ['submission:create'],
            'settings': {
                'active_year': 2026,
                'scope': unit_ahu_scope,
            },
            'active': True,
        },
        {
            'key': 'kadiv_yankum',
            'label': 'Kepala Divisi Pelayanan Hukum',
            'username': '777777777777777777',
            'email': 'agen.kadiv.yankum@kemenkum.go.id',
            'password': password,
            'roles': ['kepala_divisi'],
            'permissions': ['submission:create'],
            'settings': {
                'active_year': 2026,
                'scope': division_scope,
            },
            'active': True,
        },
    ]

    forms = [
        {
            'key': 'f1_ki',
            'code': 'MTRX-F1-KI',
            'slug': 'matrix-target-unit-ki',
            'name': 'Matrix F1 Target Unit KI',
            'description': 'Fixture manual test matriks ABAC untuk target unit KI.',
            'owner_scope': admin_scope,
            'target_scope': unit_ki_scope,
            'access_policy_key': 'form.unit_internal',
            'schema': {
                'display': 'form',
                'components': [
                    {
                        'type': 'textfield',
                        'key': 'judul_kegiatan',
                        'label': 'Judul Kegiatan',
                        'validate': {'required': True},
                        'input': True,
                    },
                    {
                        'type': 'textarea',
                        'key': 'catatan',
                        'label': 'Catatan',
                        'input': True,
                    },
                    {
                        'type': 'button',
                        'key': 'submit',
                        'label': 'Kirim',
                        'action': 'submit',
                        'input': True,
                    },
                ],
            },
        },
        {
            'key': 'f2_ahu',
            'code': 'MTRX-F2-AHU',
            'slug': 'matrix-target-unit-ahu',
            'name': 'Matrix F2 Target Unit AHU',
            'description': 'Fixture manual test matriks ABAC untuk target unit AHU.',
            'owner_scope': admin_scope,
            'target_scope': unit_ahu_scope,
            'access_policy_key': 'form.unit_internal',
            'schema': {
                'display': 'form',
                'components': [
                    {
                        'type': 'textfield',
                        'key': 'judul_kegiatan',
                        'label': 'Judul Kegiatan',
                        'validate': {'required': True},
                        'input': True,
                    },
                    {
                        'type': 'number',
                        'key': 'jumlah_layanan',
                        'label': 'Jumlah Layanan',
                        'input': True,
                    },
                    {
                        'type': 'button',
                        'key': 'submit',
                        'label': 'Kirim',
                        'action': 'submit',
                        'input': True,
                    },
                ],
            },
        },
        {
            'key': 'f3_divph',
            'code': 'MTRX-F3-DIVPH',
            'slug': 'matrix-target-divisi-pelayanan-hukum',
            'name': 'Matrix F3 Broadcast Divisi Pelayanan Hukum',
            'description': 'Fixture manual test matriks ABAC untuk target divisi Pelayanan Hukum.',
            'owner_scope': admin_scope,
            'target_scope': division_scope,
            'access_policy_key': 'form.division_broadcast',
            'schema': {
                'display': 'form',
                'components': [
                    {
                        'type': 'textfield',
                        'key': 'judul_kegiatan',
                        'label': 'Judul Kegiatan',
                        'validate': {'required': True},
                        'input': True,
                    },
                    {
                        'type': 'select',
                        'key': 'status_realisasi',
                        'label': 'Status Realisasi',
                        'input': True,
                        'data': {
                            'values': [
                                {'label': 'Belum Jalan', 'value': 'belum_jalan'},
                                {'label': 'Proses', 'value': 'proses'},
                                {'label': 'Selesai', 'value': 'selesai'},
                            ]
                        },
                    },
                    {
                        'type': 'button',
                        'key': 'submit',
                        'label': 'Kirim',
                        'action': 'submit',
                        'input': True,
                    },
                ],
            },
        },
    ]

    return {
        'password': password,
        'users': users,
        'forms': forms,
    }


def seed_matrix_test_fixture(
    password=DEFAULT_MATRIX_TEST_PASSWORD,
    user_service=None,
    user_repository=None,
    form_service=None,
    form_repository=None,
    form_version_service=None,
):
    fixture = build_matrix_fixture_payload(password=password)
    user_service = user_service or UserService()
    user_repository = user_repository or UserRepository()
    form_repository = form_repository or FormRepository()
    form_service = form_service or FormService(form_repository=form_repository)
    form_version_service = form_version_service or FormVersionService(form_repository=form_repository)

    seeded_users = []
    actor_map = {}
    for user_spec in fixture['users']:
        user = _upsert_user(user_spec, user_service=user_service, user_repository=user_repository)
        seeded_users.append(
            {
                'key': user_spec['key'],
                'label': user_spec['label'],
                'username': user.username,
                'email': user.email,
                'roles': list(user.roles or []),
                'permissions': list(user.permissions or []),
                'scope_code': ((user.settings or {}).get('scope') or {}).get('code'),
            }
        )
        actor_map[user_spec['key']] = user

    admin_actor = actor_map['admin_kanwil']
    seeded_forms = []
    for form_spec in fixture['forms']:
        form_record = _upsert_form_fixture(
            form_spec,
            actor=admin_actor,
            form_service=form_service,
            form_repository=form_repository,
            form_version_service=form_version_service,
        )
        seeded_forms.append(form_record)

    return {
        'password': password,
        'users': seeded_users,
        'forms': seeded_forms,
    }


def _upsert_user(spec, user_service=None, user_repository=None):
    user_service = user_service or UserService()
    user_repository = user_repository or UserRepository()
    existing_user = user_repository.find_one_by(username=spec['username'])

    if not existing_user:
        return user_service.register(
            username=spec['username'],
            email=spec['email'],
            password=spec['password'],
            is_seeding=True,
            roles=spec.get('roles'),
            permissions=spec.get('permissions'),
            active=spec.get('active', True),
            settings=spec.get('settings'),
        )

    existing_user.email = spec['email']
    existing_user.active = bool(spec.get('active', True))
    existing_user.roles = list(spec.get('roles') or [])
    existing_user.permissions = list(spec.get('permissions') or [])
    existing_user.settings = spec.get('settings') or {}
    existing_user.set_password(spec['password'])
    return user_repository.save(existing_user)


def _upsert_form_fixture(spec, actor, form_service=None, form_repository=None, form_version_service=None):
    form_repository = form_repository or FormRepository()
    form_service = form_service or FormService(form_repository=form_repository)
    form_version_service = form_version_service or FormVersionService(form_repository=form_repository)
    existing_form = form_repository.find_one_by(code=spec['code'])

    form_payload = {
        'code': spec['code'],
        'slug': spec['slug'],
        'name': spec['name'],
        'description': spec.get('description'),
        'visibility': 'internal',
        'owner_scope': spec.get('owner_scope'),
        'target_scope': spec.get('target_scope'),
        'access_policy_key': spec.get('access_policy_key'),
        'schema': spec.get('schema'),
    }

    if existing_form:
        form = form_service.update_form_identity(existing_form.id, form_payload, actor=actor)
    else:
        create_result = form_service.create_form(form_payload, actor=actor)
        form = create_result['form']

    draft_version = form_version_service.create_draft_version(
        form_id=form.id,
        schema=spec.get('schema'),
        actor=actor,
    )
    published_version = form_version_service.publish_version(draft_version.id, actor=actor)

    target_scope = spec.get('target_scope') or {}
    return {
        'key': spec['key'],
        'form_id': form.id,
        'code': spec['code'],
        'slug': spec['slug'],
        'name': spec['name'],
        'target_scope_type': target_scope.get('type'),
        'target_scope_code': target_scope.get('code'),
        'access_policy_key': spec.get('access_policy_key'),
        'published_version_id': getattr(published_version, 'id', None),
    }


def print_matrix_fixture_summary(result):
    print('✅ Seed fixture matriks ABAC selesai.')
    print(f"Password semua user fixture: {result['password']}")
    print('Users:')
    for user in result['users']:
        role_list = ', '.join(user['roles']) if user['roles'] else '-'
        permission_list = ', '.join(user['permissions']) if user['permissions'] else '-'
        print(
            f"- {user['label']}: username={user['username']} email={user['email']} "
            f"scope={user['scope_code']} roles={role_list} permissions={permission_list}"
        )
    print('Forms:')
    for form in result['forms']:
        print(
            f"- {form['code']} ({form['name']}): form_id={form['form_id']} "
            f"target={form['target_scope_type']}:{form['target_scope_code']} "
            f"policy={form['access_policy_key']} published_version_id={form['published_version_id']}"
        )


def parse_args():
    parser = argparse.ArgumentParser(description='Seeder proyek dasborkanwil')
    parser.add_argument(
        '--profile',
        action='append',
        choices=['employees', 'agent', 'abac_matrix', 'all'],
        help='Profile seeding yang akan dijalankan. Bisa dipakai berulang.',
    )
    parser.add_argument(
        '--matrix-password',
        default=DEFAULT_MATRIX_TEST_PASSWORD,
        help='Password yang dipakai semua user fixture matriks ABAC.',
    )
    return parser.parse_args()


def run_selected_seed_profiles(args):
    selected_profiles = args.profile or ['all']
    if 'all' in selected_profiles:
        selected_profiles = ['employees', 'agent', 'abac_matrix']

    if 'employees' in selected_profiles:
        seed_employees()
    if 'agent' in selected_profiles:
        seed_user_agents()
    if 'abac_matrix' in selected_profiles:
        result = seed_matrix_test_fixture(password=args.matrix_password)
        print_matrix_fixture_summary(result)


if __name__ == '__main__':
    from app import create_app

    arguments = parse_args()
    app = create_app(config_mode=os.getenv('FLASK_ENV', 'default'))
    with app.app_context():
        run_selected_seed_profiles(arguments)
