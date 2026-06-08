"""Repository domain employee.

Modul ini membungkus query persistence employee yang dipakai service user dan employee."""

from app.core.extensions import db
from app.core.repositories.base import BaseRepository
from .models import Employee

class EmployeeRepository(BaseRepository):
    """Repository query untuk entity Employee.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = EmployeeRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = EmployeeRepository()
        """

        super().__init__(model=Employee)
