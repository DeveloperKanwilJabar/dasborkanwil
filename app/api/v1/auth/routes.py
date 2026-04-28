from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    )
from app.modules.user.services import UserService
from app.core.extensions import db
from app.core.utils import json_response

api_auth_bp = Blueprint(
    'api_auth_v1',
    __name__,
    url_prefix='/api/v1/auth'
)

@api_auth_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json()

    try:
        service = UserService()
        service.register(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            is_seeding=False, # Pendaftaran selain seeding
        )
        return json_response(True, "Registrasi berhasil! Silahkan login.")

    except ValueError as e:
        return json_response(False, str(e), status=400)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Register Error: {str(e)}")
        return json_response(False, "Terjadi kesalahan saat menyimpan data.", status=500)


@api_auth_bp.route('/login', methods=['POST'])
def api_login():
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
def logout():
    return jsonify({"message": "Logout successful"})
