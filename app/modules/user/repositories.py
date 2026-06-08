"""Repository domain user.

Modul ini menyediakan query spesifik untuk pengecekan unik username/email dan pengambilan user."""

from app.core.extensions import db
from app.core.repositories.base import BaseRepository
from .models import User

class UserRepository(BaseRepository):
    """Repository query untuk entity User.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = UserRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = UserRepository()
        """

        super().__init__(model=User)

    def exists_username(self, username, exclude_user_id=None):
        """Mengecek apakah username sudah dipakai user lain.

        Args:
            username (Any): Username unik user target.
            exclude_user_id (Any): Primary key user yang harus dikecualikan saat cek unik.

        Returns:
            bool: Hasil evaluasi atau status sukses operasi.

        Example:
            >>> repo.exists_username(username=..., exclude_user_id=...)
        """

        query = self.model.query.filter(User.username == username)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return db.session.query(query.exists()).scalar()

    def exists_email(self, email, exclude_user_id=None):
        """Mengecek apakah email sudah dipakai user lain.

        Args:
            email (Any): Email unik user target.
            exclude_user_id (Any): Primary key user yang harus dikecualikan saat cek unik.

        Returns:
            bool: Hasil evaluasi atau status sukses operasi.

        Example:
            >>> repo.exists_email(email=..., exclude_user_id=...)
        """

        query = self.model.query.filter(User.email == email)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return db.session.query(query.exists()).scalar()

    def exists(self, username, email):
        '''Cek apakah username atau email sudah terdaftar di tabel User.'''
        # cara lama:
        # return self.model.query.filter(
        #     (self.model.username == username) | (self.model.email == email)
        # ).first() is not None
        # Gunakan .exists() untuk performa query yang lebih cepat daripada .first()
        return db.session.query(self.model.query.filter(
            (User.username == username) | (User.email == email)
        ).exists()).scalar()
