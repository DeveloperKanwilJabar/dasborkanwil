import os
import csv
import uuid
from app import db, now_utc
from app.modules.user.services import UserService
from app.modules.employee.repositories import EmployeeRepository
from app.modules.employee.services import EmployeeService
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def seed_employees():
    """Seed data pegawai dari CSV."""
    file_path = 'instance/pegawai.csv'

    # Inisialisasi service sebagai instance
    emp_service = EmployeeService()

    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            try:
                # Service sekarang handle pengecekan 'existing' secara internal
                emp_service.add(
                    nip=row['nip'],
                    name=row['full_name'],
                    unit=row['unit'],
                    skip_if_exists=True # Flag khusus agar tidak crash saat seeding
                )
                print(f"✅ OK")
            except ValueError as e:
                print(f"❌ Error: {str(e)}")
    print("✅ Seeding data pegawai selesai.")

def seed_user_agents():
    """Seed data user Agentic AI."""
    UserService().register(
        username='963214963214963214',
        email='agent_1@kemenkum.go.id',
        password='JalanJakarta#27',
        is_seeding=True,
    )
    print("✅ Seeding data agen selesai.")

if __name__ == "__main__":
    from app import create_app
    app = create_app(config_mode=os.getenv('FLASK_ENV', 'default'))
    with app.app_context():
        seed_employees()
        seed_user_agents()
