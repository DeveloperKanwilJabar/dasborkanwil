"""Endpoint autentikasi JWT untuk API v1.

Dokumentasi di modul ini membantu reviewer memahami alur register/login/logout,
parameter input, serta bentuk token yang dihasilkan untuk dipakai endpoint lain.
"""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flasgger import swag_from

from app.api.docs import body_parameter, build_spec, envelope_schema, security_bearer
from app.core.extensions import db
from app.core.utils import json_response
from app.modules.user.services import UserService

api_auth_bp = Blueprint(
    'api_auth_v1',
    __name__,
    url_prefix='/api/v1/auth'
)

REGISTER_DOC = build_spec(
    tag='Auth',
    summary='Registrasi user baru.',
    description=(
        'Digunakan untuk membuat user baru melalui API. '
        'Input: username, email, password. Output: envelope sukses sederhana '
        'tanpa token karena user tetap harus login setelah registrasi.'
    ),
    parameters=[
        body_parameter(
            'body',
            {
                'type': 'object',
                'required': ['username', 'email', 'password'],
                'properties': {
                    'username': {'type': 'string', 'example': 'budi'},
                    'email': {'type': 'string', 'example': 'budi@example.com'},
                    'password': {'type': 'string', 'example': 'PasswordRahasia123'},
                },
            },
            description='Payload registrasi user baru.',
        )
    ],
    responses={
        200: {
            'description': 'Registrasi berhasil.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Registrasi berhasil! Silahkan login.'),
        },
        400: {
            'description': 'Payload registrasi tidak valid.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Payload registrasi tidak valid.', success_example=False),
        },
        500: {
            'description': 'Kesalahan server.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Terjadi kesalahan saat menyimpan data.', success_example=False),
        },
    },
)

LOGIN_DOC = build_spec(
    tag='Auth',
    summary='Login dan dapatkan JWT access token.',
    description=(
        'Endpoint ini memverifikasi username dan password, lalu mengembalikan JWT access token. '
        'Output sukses berupa object JSON `{token: <jwt>}` yang dapat dipakai pada header '
        '`Authorization: Bearer <jwt>` saat mengakses endpoint terproteksi.'
    ),
    parameters=[
        body_parameter(
            'body',
            {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {'type': 'string', 'example': 'budi'},
                    'password': {'type': 'string', 'example': 'PasswordRahasia123'},
                },
            },
            description='Kredensial login user.',
        )
    ],
    responses={
        200: {
            'description': 'Login berhasil.',
            'schema': {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'example': 'eyJhbGciOi...'},
                },
            },
        },
        400: {
            'description': 'Payload login tidak valid.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Payload login tidak valid.', success_example=False),
        },
        401: {
            'description': 'Username/password salah.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='NIP atau Password salah.', success_example=False),
        },
        500: {
            'description': 'Kesalahan server.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Terjadi kesalahan sistem.', success_example=False),
        },
    },
)

LOGOUT_DOC = build_spec(
    tag='Auth',
    summary='Logout user berbasis JWT.',
    description=(
        'Saat ini endpoint logout hanya menjadi acknowledgement untuk client yang sudah '
        'memegang token valid. Cocok dipakai untuk menstandarkan alur UI logout.'
    ),
    parameters=[],
    responses={
        200: {
            'description': 'Logout berhasil.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Logout successful'},
                },
            },
        },
        401: {
            'description': 'Token tidak valid atau belum dikirim.',
            'schema': envelope_schema({'type': 'object', 'nullable': True}, message_example='Missing Authorization Header', success_example=False),
        },
    },
    security=security_bearer(),
)


@api_auth_bp.route('/register', methods=['POST'])
@swag_from(REGISTER_DOC)
def api_register():
    """Registrasi user baru.

    Input:
    - username: string
    - email: string
    - password: string

    Output:
    - Response JSON standar `json_response()`.
    """
    data = request.get_json()

    try:
        service = UserService()
        service.register(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            is_seeding=False,
        )
        return json_response(True, "Registrasi berhasil! Silahkan login.")

    except ValueError as e:
        return json_response(False, str(e), status=400)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Register Error: {str(e)}")
        return json_response(False, "Terjadi kesalahan saat menyimpan data.", status=500)


@api_auth_bp.route('/login', methods=['POST'])
@swag_from(LOGIN_DOC)
def api_login():
    """Login user dan kembalikan access token JWT.

    Returns:
        tuple[Response, int]: JSON `{token: ...}` bila sukses.
    """
    data = request.get_json()

    try:
        user = UserService().authenticate(data.get('username'), data.get('password'))
        if user:
            token = create_access_token(identity=str(user.id))
            return jsonify(token=token), 200

        return json_response(False, "NIP atau Password salah.", status=401)

    except ValueError as e:
        return json_response(False, str(e), status=400)

    except Exception as e:
        current_app.logger.error(f"API Login Error: {str(e)}")
        return json_response(False, "Terjadi kesalahan sistem.", status=500)


@api_auth_bp.route('/logout', methods=['POST'])
@jwt_required()
@swag_from(LOGOUT_DOC)
def logout():
    """Logout acknowledgement untuk client JWT.

    Returns:
        Response: JSON sederhana berisi pesan sukses.
    """
    _ = get_jwt_identity()
    return jsonify({"message": "Logout successful"})
