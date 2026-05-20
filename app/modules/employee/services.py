import uuid
from flask import current_app
from app.core.extensions import db
from app.core.utils import now_utc
from app.core.services.base import BaseService
from app.modules.employee.repositories import EmployeeRepository
from .models import Employee

class EmployeeService(BaseService):
    def __init__(self):
        # Inisialisasi repository utama via BaseService
        super().__init__(repository=EmployeeRepository())

    def link_user(self, employee, user):
        '''Hubungkan pegawai dengan user.'''
        if not employee or not user:
            raise ValueError("Data Pegawai atau User tidak valid.")

        employee.user = user
        return self.repository.save(employee)

    def add(self, nip, name, **kwargs):
        '''Proses pembuatan pegawai baru denga proteksi ganda.'''

        # 1. Cek duplikasi (Logika ini pindah dari seeder ke sini)
        existing = self.repository.find_one_by(nip=nip)
        if existing:
            # Jika untuk seeding, mungkin kita ingin skip saja daripada raise error
            if kwargs.get('skip_if_exists'):
                return existing
            raise ValueError(f"NIP {nip} sudah terdaftar.")
        try:
            unit = kwargs.get('unit', 'Unknown')
            new_employee = Employee(
                uuid=str(uuid.uuid4()),
                nip=nip,
                name=name,
                created_at=now_utc(),
                active=True,
                details={'unit': unit} # Simpan unit di kolom JSON
            )
            employee = self.repository.save(new_employee)
            current_app.logger.info(f"Pegawai baru berhasil dibuat: {nip} - {name}")
            return employee
        except ValueError as e:
            db.session.rollback()
            current_app.logger.error(f"Gagal membuat pegawai, DB error: {str(e)}")
            raise ValueError(str(e))
