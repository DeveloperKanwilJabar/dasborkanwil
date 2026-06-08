"""Konfigurasi aplikasi Flask lintas environment.

Modul ini mendefinisikan base config dan turunan environment yang dipakai oleh
application factory. Fokusnya bukan hanya menyimpan env var, tetapi juga
memberi kontrak konfigurasi yang mudah dibaca saat review arsitektur.
"""

import json
import locale
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Konfigurasi dasar yang diwarisi semua environment.

    Atribut pada kelas ini dipakai oleh app factory, extension Flask, JWT,
    session, mail, hingga helper dokumentasi API.
    """

    APP_NAME = os.environ.get('APP_NAME', 'Dasbor Informasi')
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'ganti-dengan-random-string-64-karakter')
    FLASK_DEBUG = False

    APP_TIMEZONE = os.environ.get('APP_TIMEZONE', 'Asia/Jakarta')
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*').split(',')

    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', '12')))

    DB_DRIVER = os.environ.get('DB_DRIVER', 'postgresql')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'dasborkanwil')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('JWT_ACCESS_HOURS', '8')))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_DAYS', '30')))
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_CSRF_PROTECT = False

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '25'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@dasborkanwil.local')

    SWAGGER = {
        'title': os.environ.get('SWAGGER_TITLE', 'Dasborkanwil API Docs'),
        'uiversion': 3,
        'openapi': '3.0.2',
    }

    FORMIO_DEFAULT_BUILDER_OPTIONS = json.loads(
        os.environ.get('FORMIO_DEFAULT_BUILDER_OPTIONS', '{}')
    )

    @staticmethod
    def build_db_uri(driver, user, password, host, port, name):
        """Bangun SQLAlchemy database URI dari komponen environment.

        Args:
            driver (str): Nama driver utama, misalnya `postgresql`, `mysql`,
                `oracle`, atau `sqlite`.
            user (str): Username database.
            password (str): Password database.
            host (str): Host database.
            port (str | int): Port database.
            name (str): Nama database/schema utama.

        Returns:
            str: SQLAlchemy URI siap pakai untuk konfigurasi aplikasi.

        Example:
            >>> Config.build_db_uri('postgresql', 'postgres', 'secret', 'db', 5432, 'appdb')
            'postgresql+psycopg2://postgres:secret@db:5432/appdb'
        """
        if driver == 'mysql':
            return f'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4'
        if driver == 'oracle':
            return f'oracle://{user}:{password}@{host}:{port}/{name}'
        if driver == 'sqlite':
            return f'sqlite:///{BASE_DIR}/app.db'
        return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}'

    @classmethod
    def init_app(cls, app):
        """Lakukan inisialisasi tambahan setelah config dibind ke Flask app.

        Saat ini hook ini dipakai untuk mencoba set locale waktu Indonesia.
        Kegagalan set locale dianggap non-fatal agar aplikasi tetap bisa boot.

        Args:
            app (flask.Flask): Instance aplikasi yang baru diinisialisasi.

        Returns:
            None

        Example:
            >>> Config.init_app(app)
        """
        try:
            target_locale = 'id_ID.utf8' if os.name != 'nt' else 'id_ID'
            locale.setlocale(locale.LC_TIME, target_locale)
        except locale.Error:
            pass


class Production(Config):
    """Konfigurasi production dengan database persisten utama."""

    TESTING = False
    SQLALCHEMY_DATABASE_URI = Config.build_db_uri(
        Config.DB_DRIVER,
        Config.DB_USER,
        Config.DB_PASSWORD,
        Config.DB_HOST,
        Config.DB_PORT,
        Config.DB_NAME,
    )


class Development(Config):
    """Konfigurasi development lokal untuk iterasi harian developer."""

    DEVELOPMENT = True
    FLASK_DEBUG = True
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = Config.build_db_uri(
        Config.DB_DRIVER,
        Config.DB_USER,
        Config.DB_PASSWORD,
        Config.DB_HOST,
        Config.DB_PORT,
        Config.DB_NAME,
    )


class Testing(Config):
    """Konfigurasi testing yang aman untuk pytest dan isolated test run."""

    TESTING = True
    LOGIN_DISABLED = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI', 'sqlite:///:memory:')


config_dict = {
    'production': Production,
    'development': Development,
    'testing': Testing,
    'default': Production,
}
