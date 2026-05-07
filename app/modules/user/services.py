import re
import uuid

from flask import current_app

from app.core.access import merge_actor_settings
from app.core.extensions import db
from app.core.security.validators import ValidationRules as Rules
from app.core.services.base import BaseService
from app.modules.employee.repositories import EmployeeRepository
from app.modules.user.repositories import UserRepository

from .models import User


class UserService(BaseService):
    def __init__(self):
        super().__init__(repository=UserRepository())
        self.emp_repo = EmployeeRepository()

    def _validate(self, data):
        """Fungsi internal untuk validasi data API/Manual."""
        if 'username' in data:
            if not re.match(Rules.NIP['regex'], str(data.get('username'))):
                raise ValueError(Rules.NIP['validators'][2].message)

        if 'password' in data and data.get('password'):
            if not re.match(Rules.PASSWORD['regex'], data['password']):
                raise ValueError(Rules.PASSWORD['validators'][2].message)
            if len(data['password']) < 8:
                raise ValueError(Rules.PASSWORD['validators'][1].message)

        if 'email' in data:
            email_val = data.get('email')
            if not re.match(Rules.EMAIL['regex'], email_val):
                raise ValueError(Rules.EMAIL['validators'][1].message)

        return True

    def _normalize_json_list(self, value):
        if value is None:
            return []

        if isinstance(value, str):
            items = value.split(',')
        elif isinstance(value, (list, tuple, set)):
            items = list(value)
        else:
            items = [value]

        normalized = []
        seen = set()
        for item in items:
            cleaned = str(item).strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def register(
        self,
        username,
        email,
        password,
        is_seeding=False,
        roles=None,
        permissions=None,
        active=True,
        settings=None,
    ):
        """
        Pintu tunggal pendaftaran user.
        - Jika is_seeding=True: Lewati validasi Employee & Linking.
        - Jika is_seeding=False: Wajib ada di Master Employee & otomatis Linking.
        """
        current_app.logger.debug(
            f"Validating registration data. Username: {username}, Email: {email}, Is Seeding: {is_seeding}"
        )
        self._validate({'username': username, 'email': email, 'password': password})

        employee = None
        if not is_seeding:
            employee = self.emp_repo.find_one_by(nip=username)
            if not employee:
                current_app.logger.warning(
                    f"Ada percobaan registrasi dengan NIP yang tidak terdaftar di pegawai: {username}"
                )
                raise ValueError('NIP tidak terdaftar di data pegawai.')

            if not employee.active:
                current_app.logger.warning(
                    f"Ada percobaan registrasi dengan NIP pegawai nonaktif: {username}"
                )
                raise ValueError('Status pegawai sudah nonaktif.')

        if self.repository.exists_username(username):
            current_app.logger.warning(f"Ada percobaan registrasi dengan NIP sudah terdaftar: {username}")
            raise ValueError('NIP sudah terdaftar. Gunakan NIP lain.')

        if self.repository.exists_email(email):
            current_app.logger.warning(f"Ada percobaan registrasi dengan email sudah terdaftar: {email}")
            raise ValueError('Email sudah terdaftar. Gunakan email lain.')

        try:
            new_user = User(
                uuid=str(uuid.uuid4()),
                username=username,
                email=email,
                active=bool(active),
                roles=self._normalize_json_list(roles),
                permissions=self._normalize_json_list(permissions),
                settings=merge_actor_settings(settings),
            )
            new_user.set_password(password)

            user = self.repository.save(new_user)

            if not is_seeding and employee:
                employee.user = user
                self.emp_repo.save(employee)
                current_app.logger.info(f"Linking sukses: User {username} -> Pegawai {employee.nip}")

            current_app.logger.info(f"User baru berhasil didaftarkan: {username}")
            return user
        except ValueError as e:
            db.session.rollback()
            current_app.logger.error(f"Gagal registrasi user, DB error: {str(e)}")
            raise ValueError(str(e))

    def update_user(self, user_id, email, active, roles=None, permissions=None, password=None, settings=None):
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError('User tidak ditemukan.')

        payload = {'email': email}
        if password:
            payload['password'] = password
        self._validate(payload)

        if self.repository.exists_email(email, exclude_user_id=user.id):
            raise ValueError('Email sudah terdaftar. Gunakan email lain.')

        user.email = email
        user.active = bool(active)
        user.roles = self._normalize_json_list(roles)
        user.permissions = self._normalize_json_list(permissions)
        user.settings = merge_actor_settings(settings)

        if password:
            user.set_password(password)

        try:
            updated_user = self.repository.save(user)
            current_app.logger.info(f"User berhasil diperbarui: {user.username}")
            return updated_user
        except ValueError as e:
            db.session.rollback()
            current_app.logger.error(f"Gagal update user {user.username}: {str(e)}")
            raise ValueError(str(e))

    def authenticate(self, username, password):
        '''Fungsi tunggal untuk validasi kredensial'''
        self._validate({'username': username, 'password': password})

        user = self.repository.find_one_by(username=username)

        if user and user.check_password(password):
            current_app.logger.info(f"Authentication success. Username: {username}")
            return user

        current_app.logger.warning(f"Authentication failed. Username: {username}")
        return None
