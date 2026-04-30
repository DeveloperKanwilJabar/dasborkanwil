from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.core.utils import json_response
from app.modules.user.services import UserService

api_user_bp = Blueprint(
    'api_user_v1',
    __name__,
    url_prefix='/api/v1/user'
)

@api_user_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """Endpoint untuk mendapatkan detail user (JSON)"""
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
def user_all():
    """Endpoint untuk mendapatkan semua data user (JSON)"""
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
