"""Middleware dan bootstrap logging aplikasi.

Modul ini memusatkan hook Flask `before_request` dan setup logger agar perilaku
lintas route tetap konsisten serta mudah diuji/didokumentasikan.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import current_app, request
from flask_login import current_user

from .extensions import db
from .utils import now_utc


def setup_request(app):
    """Daftarkan hook request global pada aplikasi Flask.

    Hook yang dipasang saat ini mencakup:
    - pembaruan `last_login` untuk user yang sedang terautentikasi,
    - logging ringan untuk request API v1.

    Args:
        app (flask.Flask): Instance aplikasi yang akan dipasangi middleware.

    Returns:
        None

    Example:
        >>> app = Flask(__name__)
        >>> setup_request(app)
    """

    @app.before_request
    def handle_before_request():
        """Perbarui jejak login user aktif sebelum request diproses.

        Saat user sudah login, field `last_login` diset ke UTC sekarang sebagai
        jejak aktivitas terakhir. Untuk versi saat ini, perubahan langsung di-
        commit pada setiap request terautentikasi.
        """
        if current_user.is_authenticated:
            current_user.last_login = now_utc()
            db.session.commit()

    @app.before_request
    def handle_api_request():
        """Tulis log request masuk untuk endpoint API v1.

        Log ini membantu observability dasar saat review bug atau audit trafik
        endpoint internal.
        """
        if request.path.startswith('/api/v1/'):
            current_app.logger.info("API Request: %s %s", request.method, request.path)


def setup_logging(app):
    """Siapkan file handler dan stream handler untuk logger aplikasi.

    Logger ditulis ke dua tujuan sekaligus:
    - `logs/app.log` untuk jejak persisten,
    - stdout/stderr terminal untuk observasi saat development atau container log.

    Args:
        app (flask.Flask): Instance aplikasi Flask yang logger-nya akan
            dikonfigurasi.

    Returns:
        None

    Example:
        >>> app = Flask(__name__)
        >>> setup_logging(app)
        >>> app.logger.level == logging.INFO
        True
    """
    if not os.path.exists('logs'):
        os.mkdir('logs')

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )

    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
