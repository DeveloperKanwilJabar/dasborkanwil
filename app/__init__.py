import os
import logging
from logging.handlers import RotatingFileHandler
from flask import (
    Flask, Blueprint, current_app, request,
    redirect, url_for, render_template,
    )

# Impor eksplisit (No Star Import!)
from .libs import (
    db, migrate, bcrypt, login_manager,
    csrf, mail, cors, UserMixin, current_user,
    login_user, login_required, logout_user,
    )
from .helpers import (
    now_utc,
    )

def create_app(config_class=None):
    app = Flask(
        __name__,
        static_url_path='/static',
        static_folder='static',
        template_folder='templates',
        )

    if config_class:
        app.config.from_object(config_class)

    # Inisialisasi Ekstensi
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    # Inisialisasi CORS jika ingin default (izinkan semua), cukup:
    # cors.init_app(app)
    # Saran spesifik (untuk keamanan):
    cors.init_app(app, resources={r"/api/*": {"origins": app.config['CORS_ALLOWED_ORIGINS']}})

    login_manager.init_app(app)
    # login_manager.login_view = 'user.login'
    # login_manager.login_message_category = "warning"

    # Logging Setup (Gunakan Path yang jelas)
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

    with app.app_context():

        @app.route('/')
        def index():
            return render_template('pages/index.html')

    return app
