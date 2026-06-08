"""Registrasi seluruh extension Flask yang dipakai aplikasi.

Setiap instance dideklarasikan tanpa binding ke `app` agar kompatibel dengan
application factory pattern pada `create_app()`. Dengan pola ini, test, CLI,
dan beberapa environment bisa memakai extension yang sama tanpa side effect
saat import module.
"""

from app.api.docs import swagger_config, swagger_template

from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flasgger import Swagger

# Instance dideklarasikan global agar dapat di-import lintas module lalu di-bind
# sekali pada application factory.
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
cors = CORS()
jwt = JWTManager()
swagger = Swagger(config=swagger_config(), template=swagger_template())
