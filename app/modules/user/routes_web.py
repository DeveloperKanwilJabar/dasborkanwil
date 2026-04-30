from flask import Blueprint, current_app, jsonify, make_response, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
from flask_login import current_user, login_required, login_user, logout_user

from app.core.extensions import db
from app.core.utils import json_response

from .forms import LoginForm, RegisterForm, UserCreateForm, UserUpdateForm
from .services import UserService

user_bp = Blueprint(
    'user',
    __name__,
    template_folder='pages',
)


def _first_form_error(form, fallback='Validasi gagal.'):
    for _, messages in form.errors.items():
        if messages:
            return messages[0]
    return fallback


def _serialize_user(user, include_audit=False):
    payload = {
        'id': user.id,
        'uuid': user.uuid,
        'username': user.username,
        'email': user.email,
        'active': user.active,
        'email_verified_at': str(user.email_verified_at) if user.email_verified_at else None,
        'last_login': str(user.last_login) if user.last_login else None,
        'roles': user.roles or [],
        'permissions': user.permissions or [],
    }

    if include_audit:
        payload.update(
            {
                'created_at': str(user.created_at) if user.created_at else None,
                'updated_at': str(user.updated_at) if user.updated_at else None,
            }
        )

    return payload


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        current_app.logger.info('Register form validation passed.')

        try:
            service = UserService()
            service.register(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                is_seeding=False,
            )
            return json_response(
                True,
                'Registrasi berhasil! Silahkan login.',
                {'redirect_url': url_for('user.dashboard')},
            )

        except ValueError as e:
            return json_response(False, str(e), status=400)

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Register Error: {str(e)}')
            return json_response(False, 'Terjadi kesalahan saat menyimpan data.', status=500)

    if form.errors:
        current_app.logger.warning(f'Register form validation failed: {form.errors}')
        return json_response(False, _first_form_error(form), status=422)

    return render_template('pages/auth/register.html', form=form)


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))

    if form.validate_on_submit():
        try:
            service = UserService()
            user = service.authenticate(username=form.username.data, password=form.password.data)

            if not user:
                return json_response(False, 'NIP atau Password salah.', status=401)

            login_user(user, remember=form.remember.data)
            response = jsonify(
                {
                    'success': True,
                    'message': 'Login berhasil! Mengarahkan...',
                    'data': {'redirect_url': url_for('user.dashboard')},
                }
            )
            token = create_access_token(identity=str(user.id))
            set_access_cookies(response, token)
            current_app.logger.info(f'User logged in: {user.username}')

            return response

        except ValueError as e:
            return json_response(False, str(e), status=400)

        except Exception as e:
            current_app.logger.error(f'Login System Error: {str(e)}')
            return json_response(False, 'Terjadi kesalahan sistem saat login.', status=500)

    if form.errors:
        current_app.logger.warning(f'Login form validation failed: {form.errors}')
        return json_response(False, _first_form_error(form), status=422)

    return render_template('pages/auth/login.html', form=form)


@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    response = make_response(redirect(url_for('user.login')))
    unset_jwt_cookies(response)
    current_app.logger.info('User logged out and JWT cookies cleared.')
    return response


@user_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_authenticated:
        current_app.logger.warning('Unauthorized access attempt to dashboard.')
        return redirect(url_for('user.login'))

    return render_template('pages/user/dashboard.html', user=current_user)


@user_bp.route('/users/index')
@login_required
def index():
    form = UserUpdateForm()
    return render_template('pages/user/user_index.html', form=form)


@user_bp.route('/profile')
@login_required
def profile():
    return render_template('pages/user/profile.html', user=current_user)


@user_bp.route('/users/data', methods=['GET'])
@login_required
def users_data():
    try:
        users = UserService().get_all()
        return jsonify([_serialize_user(user) for user in users])
    except Exception as e:
        current_app.logger.error(f'Error getting users data: {str(e)}')
        return json_response(False, 'Gagal mengambil data users.', status=500)


@user_bp.route('/users/data/<int:user_id>', methods=['GET'])
@login_required
def user_data(user_id):
    try:
        user = UserService().repository.get_by_id(user_id)
        if not user:
            return json_response(False, 'User tidak ditemukan.', status=404)

        return jsonify(_serialize_user(user, include_audit=True))
    except Exception as e:
        current_app.logger.error(f'Error getting user data: {str(e)}')
        return json_response(False, 'Gagal mengambil data user.', status=500)


@user_bp.route('/users/create', methods=['POST'])
@login_required
def user_create():
    form = UserCreateForm(meta={'csrf': False})

    if not form.validate():
        return json_response(False, _first_form_error(form), status=422)

    try:
        service = UserService()
        user = service.register(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            roles=form.roles.data,
            permissions=form.permissions.data,
            active=form.active.data,
            is_seeding=False,
        )

        return json_response(True, 'User berhasil dibuat.', _serialize_user(user))
    except ValueError as e:
        current_app.logger.warning(
            f'User creation failed: {str(e)}, username: {form.username.data}, email: {form.email.data}'
        )
        return json_response(False, str(e), status=400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating user: {str(e)}')
        return json_response(False, 'Terjadi kesalahan saat menyimpan data.', status=500)


@user_bp.route('/users/update/<int:user_id>', methods=['PUT', 'PATCH'])
@login_required
def user_update(user_id):
    form = UserUpdateForm(meta={'csrf': False})

    if not form.validate():
        return json_response(False, _first_form_error(form), status=422)

    try:
        service = UserService()
        user = service.update_user(
            user_id=user_id,
            email=form.email.data,
            active=form.active.data,
            roles=form.roles.data,
            permissions=form.permissions.data,
            password=form.password.data,
        )

        return json_response(True, 'User berhasil diupdate.', _serialize_user(user))
    except ValueError as e:
        current_app.logger.warning(f'User update failed: {str(e)}, user_id: {user_id}')
        return json_response(False, str(e), status=400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating user: {str(e)}')
        return json_response(False, 'Gagal mengupdate user.', status=500)


@user_bp.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def user_delete(user_id):
    try:
        service = UserService()
        user = service.repository.get_by_id(user_id)
        if not user:
            return json_response(False, 'User tidak ditemukan.', status=404)

        service.repository.delete(user)

        return json_response(True, 'User berhasil dihapus.', {'id': user_id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting user: {str(e)}')
        return json_response(False, 'Gagal menghapus user.', status=500)
