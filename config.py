import os
import json
import locale
from datetime import timedelta
from pathlib import Path

# Gunakan Pathlib untuk navigasi filesystem yang lebih bersih
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Konfigurasi Dasar (Base Config)"""
    # Identitas & Keamanan
    APP_NAME = os.environ.get('APP_NAME', 'Dasbor Informasi')
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-key-very-secret')
    # Timezone & Locale
    APP_TIMEZONE = os.environ.get('APP_TIMEZONE', 'Asia/Jakarta')
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*').split(',')

    # === REDIS & SESSION ===
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    SESSION_TYPE = 'redis'
    # Prefix unik agar tidak campur dengan aplikasi lain di Redis
    SESSION_KEY_PREFIX = 'dasborkanwil_session:'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # === GIS & DATA HANDLING ===
    # Karena ada Geopandas & Folium, folder ini untuk cache/data spatial
    DATA_STORAGE_PATH = os.path.join(BASE_DIR, 'storage', 'spatial_data')

    # Database Defaults (Diambil langsung dari env)
    DB_DRIVER = os.environ.get('DB_DRIVER', 'pgsql')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME')

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    @staticmethod
    def build_db_uri(driver, user, password, host, port, name):
        """Helper untuk membangun Database URI secara dinamis"""
        if driver == 'mysql':
            return f'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4'
        elif driver == 'oracle':
            return f'oracle://{user}:{password}@{host}:{port}/{name}'
        elif driver == 'sqlite':
            return f'sqlite:///{BASE_DIR}/attendance.db'
        # Default ke PostgreSQL
        return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}'

    @classmethod
    def init_app(cls, app):
        """Inisialisasi tambahan jika diperlukan"""
        try:
            # Set locale lebih aman
            target_locale = 'id_ID.utf8' if os.name != 'nt' else 'id_ID'
            locale.setlocale(locale.LC_TIME, target_locale)
        except locale.Error:
            pass

class Production(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = Config.build_db_uri(
        Config.DB_DRIVER, Config.DB_USER, Config.DB_PASSWORD,
        Config.DB_HOST, Config.DB_PORT, Config.DB_NAME
    )

class Development(Config):
    DEVELOPMENT = True
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # Bisa override DB khusus dev jika perlu
    SQLALCHEMY_DATABASE_URI = Config.build_db_uri(
        Config.DB_DRIVER, Config.DB_USER, Config.DB_PASSWORD,
        Config.DB_HOST, Config.DB_PORT, Config.DB_NAME
    )

# Mapping untuk memudahkan pemanggilan di run.py
config_dict = {
    'production': Production,
    'development': Development,
    'default': Production
}
