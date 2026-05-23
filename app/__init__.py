
from flask import Flask, render_template

# Impor eksplisit (No Star Import!)
from .core.extensions import (
    db, migrate, bcrypt, login_manager,
    csrf, mail, cors, jwt
    )
from .core.utils import (
    json_response, now_utc,
    )
from .core.middleware import setup_request, setup_logging
from .core.config import config_dict

def create_app(config_mode='default'):
    app = Flask(
        __name__,
        static_url_path='/static',
        static_folder='static',
        template_folder='templates',
        )

    if config_mode:
        config_obj = config_dict.get(config_mode, config_dict['default'])
        app.config.from_object(config_obj)

    # 1. Inisialisasi Ekstensi (Ditarik dari core/extensions.py)
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    # Inisialisasi CORS jika ingin default (izinkan semua), cukup:
    # cors.init_app(app)
    # Saran spesifik (untuk keamanan):
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ALLOWED_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
            }
        })

    login_manager.init_app(app)
    login_manager.login_view = 'user.login'
    login_manager.login_message_category = "warning"

    # 2. Setup Global Middleware & Handlers
    setup_logging(app)
    setup_request(app)

    with app.app_context():
        # Import model tambahan agar terdaftar di SQLAlchemy metadata untuk autogenerate migration
        from .modules.data_registry.models import DataRegistry, DataRegistryVersion, DataRegistryRecord
        from .modules.form.models import Form, FormVersion
        from .modules.import_pipeline.models import ImportBatch, ImportBatchRow
        from .modules.submission.models import ReportingPeriod, Submission, SubmissionEvent

        # Registrasi Blueprint
        from .api.v1.auth.routes import api_auth_bp
        from .api.v1.data_registries.routes import api_data_registry_bp
        from .api.v1.forms.routes import api_form_bp
        from .api.v1.submissions.routes import api_submission_bp
        from .modules.user.routes_web import user_bp
        from .api.v1.users.routes import api_user_bp
        from .modules.employee.routes_web import employee_bp
        from .modules.form.routes_web import form_web_bp
        from .modules.data_registry.routes_web import data_registry_web_bp

        # web routes
        app.register_blueprint(user_bp)
        app.register_blueprint(employee_bp)
        app.register_blueprint(form_web_bp)
        app.register_blueprint(data_registry_web_bp)

        # api routes
        app.register_blueprint(api_auth_bp)
        csrf.exempt(api_auth_bp) # Menonaktifkan CSRF untuk semua route di api_auth_bp
        app.register_blueprint(api_user_bp)
        csrf.exempt(api_user_bp) # Menonaktifkan CSRF untuk semua route di api_user_bp
        app.register_blueprint(api_form_bp)
        csrf.exempt(api_form_bp) # Menonaktifkan CSRF untuk semua route di api_form_bp
        app.register_blueprint(api_submission_bp)
        csrf.exempt(api_submission_bp) # Menonaktifkan CSRF untuk semua route di api_submission_bp
        app.register_blueprint(api_data_registry_bp)
        csrf.exempt(api_data_registry_bp) # Menonaktifkan CSRF untuk semua route di api_data_registry_bp

        # Services untuk Flask-Login & Shell
        from .modules.user.services import UserService
        from .modules.employee.services import EmployeeService

        @login_manager.user_loader
        def load_user(user_id):
            return UserService().repository.get_by_id(int(user_id))

    @app.route('/')
    def index():
        return render_template('pages/index.html')

    return app
