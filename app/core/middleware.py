import os
import logging
from logging.handlers import RotatingFileHandler
from flask import request, current_app, jsonify
from flask_login import current_user
from .utils import now_utc
from .extensions import db

def setup_request(app):
    # OPTIMASI: Hanya update last_login jika user login & bukan request file statis
    @app.before_request
    def handle_before_request():
        if current_user.is_authenticated:
            # Cek agar tidak commit di setiap hit (misal: update tiap 5 menit saja)
            # Untuk kesederhanaan, kita update tapi pastikan ini bukan static file
            current_user.last_login = now_utc()
            db.session.commit()

    @app.before_request
    def handle_api_request():
        # Logic khusus untuk jalur API
        if request.path.startswith('/api/v1/'):
            # Contoh: Cek custom header atau logging khusus
            current_app.logger.info(f"API Request: {request.method} {request.path}")

def setup_logging(app):
    # Logging Setup (Gunakan Path yang jelas)
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # if not app.debug and not app.testing:
        # letakkan kode di bawah disini agar hanya aktif di production (opsional)

    # Buat formatter yang detail
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    # # FORMATTER: %(pathname)s akan memberikan path lengkap.
    # # Jika ingin lebih spesifik, gunakan format ini:
    # formatter = logging.Formatter(
    #     '%(asctime)s %(levelname)s: %(message)s [in %(module)s.py:%(lineno)d]'
    # )

    # 1. File Handler (Untuk menyimpan ke logs/app.log)
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 2. Stream Handler (Untuk mencetak ke terminal debug)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    # Tambahkan keduanya ke app.logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
