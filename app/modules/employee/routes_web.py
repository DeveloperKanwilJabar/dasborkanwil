from flask import (
    Blueprint, abort, current_app, flash,
    jsonify, redirect, request, render_template, url_for,
    )
from flask_login import current_user, login_user, login_required, logout_user
from app.core.extensions import db, bcrypt
from app.core.utils import json_response, now_utc

from app.modules.employee.models import Employee

employee_bp = Blueprint(
    'employee',
    __name__,
    template_folder='pages',
)
