"""Model ORM domain user.

Modul ini mendefinisikan entity User yang dipakai untuk autentikasi, otorisasi, pengaturan actor, dan relasi ke employee."""

import uuid
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from app.core.extensions import db, bcrypt

class User(db.Model, UserMixin):
    """Masterdata Pengguna"""
    __tablename__ = 'users'

    ## kolom ##
    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False)
    username = db.Column('username', db.String(18), nullable=False, index=True, unique=True)
    password = db.Column('password', db.String(191), nullable=False)
    email = db.Column('email', db.String(120), nullable=False, unique=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    email_verified_at = db.Column('email_verified_at', db.DateTime(timezone=True))
    last_login = db.Column('last_login', db.DateTime(timezone=True))
    roles = db.Column('roles', JSONB, nullable=True)
    permissions = db.Column('permissions', JSONB, nullable=True)
    settings = db.Column('settings', JSONB, nullable=True)
    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    # Relasi ke model Employee
    employee = relationship('Employee', back_populates='user', uselist=False, lazy='joined')  # Eager loading

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return "{}({}) ".format(self.username, self.id)

    def set_password(self, password):
        """Meng-hash password plaintext sebelum disimpan ke database.

        Args:
            password (Any): Password plaintext untuk hashing atau verifikasi.

        Returns:
            None: Method memutakhirkan state object langsung di memori.

        Example:
            >>> obj.set_password(password=...)
        """

        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Memverifikasi password plaintext terhadap hash yang tersimpan.

        Args:
            password (Any): Password plaintext untuk hashing atau verifikasi.

        Returns:
            bool: Hasil evaluasi atau status sukses operasi.

        Example:
            >>> obj.check_password(password=...)
        """

        return bcrypt.check_password_hash(self.password, password)
