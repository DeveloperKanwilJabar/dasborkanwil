from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, current_user,
    login_user, login_required, logout_user,
    )
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Inisialisasi instance tanpa 'app' (Pattern Factory)
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
cors = CORS()
jwt = JWTManager()
