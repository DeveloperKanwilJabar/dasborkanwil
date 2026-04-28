from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    )
from app.modules.user.services import UserService

api_user_bp = Blueprint(
    'api_user_v1',
    __name__,
    url_prefix='/api/v1/user'
)

@api_user_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    user = UserService().repository.get_by_id(current_user)
    dict = {
        "nip": user.username,
        "email": user.email,
        "name": user.employee.name if user.employee else None,
        "unit": user.employee.details["unit"] if user.employee else None
    }
    return dict
