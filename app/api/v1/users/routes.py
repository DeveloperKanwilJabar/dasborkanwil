"""Endpoint user API berbasis JWT.

Endpoint di modul ini dipakai untuk membaca profil user aktif dan daftar user.
Setiap endpoint didokumentasikan agar reviewer paham input auth, bentuk output,
dan contoh penggunaan sederhana.
"""

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from flasgger import swag_from

from app.api.docs import build_spec, envelope_schema, security_bearer
from app.core.utils import json_response
from app.modules.user.services import UserService

api_user_bp = Blueprint(
    'api_user_v1',
    __name__,
    url_prefix='/api/v1/user'
)

USER_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer', 'example': 7},
        'uuid': {'type': 'string', 'example': 'user-uuid'},
        'username': {'type': 'string', 'example': 'budi'},
        'email': {'type': 'string', 'example': 'budi@example.com'},
        'active': {'type': 'boolean', 'example': True},
        'email_verified_at': {'type': 'string', 'nullable': True},
        'last_login': {'type': 'string', 'nullable': True},
        'roles': {'type': 'array', 'items': {'type': 'string'}, 'example': ['admin']},
        'permissions': {'type': 'array', 'items': {'type': 'string'}, 'example': ['forms.read']},
        'created_at': {'type': 'string', 'nullable': True},
        'updated_at': {'type': 'string', 'nullable': True},
    },
}

PROFILE_DOC = build_spec(
    tag='Users',
    summary='Ambil profil user aktif berdasarkan JWT.',
    description=(
        'Endpoint ini membaca identity dari JWT, lalu mengembalikan profil lengkap user aktif. '
        'Cocok untuk bootstrap session frontend setelah login.'
    ),
    parameters=[],
    responses={
        200: {'description': 'Profil berhasil diambil.', 'schema': USER_SCHEMA},
        401: {
            'description': 'Token tidak valid atau belum dikirim.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Missing Authorization Header', success_example=False),
        },
        404: {
            'description': 'User tidak ditemukan.',
            'schema': {'type': 'object', 'properties': {'error': {'type': 'string', 'example': 'User tidak ditemukan'}}},
        },
        500: {
            'description': 'Kesalahan server.',
            'schema': {'type': 'object', 'properties': {'error': {'type': 'string', 'example': 'Gagal mengambil data user'}}},
        },
    },
    security=security_bearer(),
)

ALL_USERS_DOC = build_spec(
    tag='Users',
    summary='Ambil daftar seluruh user.',
    description=(
        'Endpoint read-only untuk kebutuhan admin grid/listing user. '
        'Output berupa array object user tanpa envelope `json_response()`.'
    ),
    parameters=[],
    responses={
        200: {'description': 'Daftar user berhasil diambil.', 'schema': {'type': 'array', 'items': USER_SCHEMA}},
        401: {
            'description': 'Token tidak valid atau belum dikirim.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Missing Authorization Header', success_example=False),
        },
        500: {
            'description': 'Kesalahan server.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Gagal mengambil data users', success_example=False),
        },
    },
    security=security_bearer(),
)


@api_user_bp.route('/profile', methods=['GET'])
@jwt_required()
@swag_from(PROFILE_DOC)
def profile():
    """Endpoint untuk mendapatkan detail user aktif (JSON).

    Output:
    - object user lengkap berdasarkan identity JWT.

    Contoh penggunaan:
    - GET /api/v1/user/profile dengan header Authorization Bearer token.
    """
    try:
        current_user = get_jwt_identity()
        user = UserService().repository.get_by_id(current_user)
        if not user:
            return jsonify({'error': 'User tidak ditemukan'}), 404

        data = {
            'id': user.id,
            'uuid': user.uuid,
            'username': user.username,
            'email': user.email,
            'active': user.active,
            'email_verified_at': str(user.email_verified_at) if user.email_verified_at else None,
            'last_login': str(user.last_login) if user.last_login else None,
            'roles': user.roles,
            'permissions': user.permissions,
            'created_at': str(user.created_at) if user.created_at else None,
            'updated_at': str(user.updated_at) if user.updated_at else None,
        }
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Error getting user data: {str(e)}")
        return jsonify({'error': 'Gagal mengambil data user'}), 500


@api_user_bp.route('/all', methods=['GET'])
@jwt_required()
@swag_from(ALL_USERS_DOC)
def user_all():
    """Endpoint untuk mendapatkan semua data user (JSON).

    Returns:
        Response: Array JSON user untuk grid/list admin.
    """
    try:
        users = UserService().get_all()
        data = [
            {
                'id': u.id,
                'uuid': u.uuid,
                'username': u.username,
                'email': u.email,
                'active': u.active,
                'email_verified_at': str(u.email_verified_at) if u.email_verified_at else None,
                'last_login': str(u.last_login) if u.last_login else None,
                'roles': u.roles,
                'permissions': u.permissions,
            }
            for u in users
        ]
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Error getting users data: {str(e)}")
        return json_response(False, "Gagal mengambil data users", error=str(e)), 500
