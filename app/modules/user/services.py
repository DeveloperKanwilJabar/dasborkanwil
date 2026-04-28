import re
import uuid
from flask import current_app
from app.core.extensions import db
from app.core.security.validators import ValidationRules as Rules
from app.core.services.base import BaseService
from app.modules.employee.repositories import EmployeeRepository
from app.modules.user.repositories import UserRepository
from .models import User

class UserService(BaseService):
    def __init__(self):
        # Inisialisasi repository utama via BaseService
        super().__init__(repository=UserRepository())
        # Inisialisasi repository tambahan untuk linking
        self.emp_repo = EmployeeRepository()

    def _validate(self, data):
        """Fungsi internal untuk validasi data API/Manual"""
        # Cek NIP
        if 'username' in data:
            if not re.match(Rules.NIP['regex'], str(data.get('username'))):
                raise ValueError(Rules.NIP['validators'][2].message)

        # Cek Password
        if 'password' in data:
            if not re.match(Rules.PASSWORD['regex'], data['password']):
                raise ValueError(Rules.PASSWORD['validators'][2].message)

        # Cek Email
        if 'email' in data:
            email_val = data.get('email')
            if not re.match(Rules.EMAIL['regex'], email_val):
                raise ValueError(Rules.EMAIL['validators'][1].message)

        return True

    def register(self, username, email, password, is_seeding=False):
        """
        Pintu tunggal pendaftaran user.
        - Jika is_seeding=True: Lewati validasi Employee & Linking.
        - Jika is_seeding=False: Wajib ada di Master Employee & otomatis Linking.
        """
        # validasi awal untuk memastikan data yang masuk benar sebelum cek database
        self._validate({'username': username, 'email': email, 'password': password})

        employee = None
        # 1. Cek apakah NIP terdaftar di Master Data Employee (Hanya jika bukan seeding)
        if not is_seeding:
            employee = self.emp_repo.find_one_by(nip=username)
            if not employee:
                current_app.logger.warning(f"Ada percobaan registrasi dengan NIP tidak terdaftar: {username}")
                raise ValueError("NIP tidak terdaftar di database pegawai.")

        # 2. Cek apakah NIP atau Email sudah punya akun di tabel User
        if self.repository.exists(username, email):
            current_app.logger.warning(f"Ada percobaan registrasi dengan NIP atau Email sudah terdaftar: {username} / {email}")
            raise ValueError("NIP atau Email sudah pernah didaftarkan.")

        # 3. Create instance & save
        try:
            # A. Buat Instance User
            new_user = User(
                uuid=str(uuid.uuid4()),
                username=username,
                email=email
            )
            new_user.set_password(password)

            # B. Simpan User (Atomic Part 1)
            user = self.repository.save(new_user)

            # C. Jalankan Linking jika ini pendaftaran resmi (Atomic Part 2)
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

    def authenticate(self, username, password):
        '''Fungsi tunggal untuk validasi kredensial'''
        # validasi awal untuk memastikan data yang masuk benar sebelum cek database
        self._validate({'username': username, 'password': password})

        user = self.repository.find_one_by(username=username)

        if user and user.check_password(password):
            current_app.logger.info(f"Authentication success. Username: {username}")
            return user

        current_app.logger.warning(f"Authentication failed. Username: {username}")
        return None
