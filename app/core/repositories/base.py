"""Repository base bersama untuk semua domain.

Modul ini menyediakan operasi CRUD, pencarian dinamis, pagination,
soft delete, dan primitive persistence yang dipakai repository spesifik
setiap domain.
"""

from sqlalchemy import desc

from app.core.extensions import db
from app.core.utils import now_utc


class BaseRepository:
    """Basis repository generik untuk operasi persistence lintas domain.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> repo = BaseRepository(model=MyModel)
    """

    def __init__(self, model):
        """Inisialisasi repository generik dengan model target.

        Args:
            model (Any): Class SQLAlchemy model yang menjadi target repository.

        Returns:
            None: Konstruktor hanya menyimpan referensi model ke instance.

        Example:
            >>> repo = BaseRepository(model=MyModel)
        """
        self.model = model

    def get_all(self, include_deleted=False):
        """Mengambil seluruh record dari model target.

        Args:
            include_deleted (Any): Jika True, record soft delete ikut disertakan.

        Returns:
            list[Any]: Daftar seluruh object hasil query.

        Example:
            >>> repo.get_all(include_deleted=False)
        """
        query = self.model.query
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.all()

    def get_by_id(self, id):
        """Mengambil satu record berdasarkan primary key internal.

        Args:
            id (Any): Primary key internal record target.

        Returns:
            Any | None: Object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_id(id=123)
        """
        return db.session.get(self.model, id)

    def count(self, include_deleted=False):
        """Menghitung total record model target.

        Args:
            include_deleted (Any): Jika True, record soft delete ikut dihitung.

        Returns:
            int: Jumlah record hasil query.

        Example:
            >>> repo.count(include_deleted=False)
        """
        query = self.model.query
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.count()

    def find_by(self, include_deleted=False, **filters):
        """Mencari banyak record berdasarkan filter dinamis sederhana.

        Args:
            include_deleted (Any): Jika True, record soft delete ikut disertakan.
            filters (Any): Kumpulan filter `filter_by` SQLAlchemy berbentuk keyword args.

        Returns:
            list[Any]: Daftar object hasil query yang bisa kosong.

        Example:
            >>> repo.find_by(active=True, status='published')
        """
        query = self.model.query.filter_by(**filters)
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.all()

    def find_one_by(self, include_deleted=False, **filters):
        """Mencari satu record pertama berdasarkan filter dinamis sederhana.

        Args:
            include_deleted (Any): Jika True, record soft delete ikut disertakan.
            filters (Any): Kumpulan filter `filter_by` SQLAlchemy berbentuk keyword args.

        Returns:
            Any | None: Object pertama yang cocok atau None bila tidak ada.

        Example:
            >>> repo.find_one_by(username='198001011234567890')
        """
        query = self.model.query.filter_by(**filters)
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.first()

    def paginate(self, page=1, per_page=10, include_deleted=False, order_by_desc=True):
        """Mengambil data dalam bentuk pagination standar Flask-SQLAlchemy.

        Args:
            page (Any): Nomor halaman yang ingin diambil.
            per_page (Any): Jumlah item per halaman.
            include_deleted (Any): Jika True, record soft delete ikut disertakan.
            order_by_desc (Any): Jika True, urutkan descending berdasarkan created_at bila ada.

        Returns:
            Pagination: Objek pagination Flask-SQLAlchemy.

        Example:
            >>> repo.paginate(page=1, per_page=20)
        """
        query = self.model.query

        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)

        if order_by_desc and hasattr(self.model, 'created_at'):
            query = query.order_by(desc(self.model.created_at))

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def save(self, obj):
        """Menyimpan object ke database dan langsung commit transaksi.

        Args:
            obj (Any): Instance model yang akan disimpan.

        Returns:
            Any: Object yang sudah dipersist dan di-commit.

        Example:
            >>> repo.save(obj=my_model)
        """
        db.session.add(obj)
        db.session.commit()
        return obj

    def delete(self, obj):
        """Menghapus object secara soft delete atau hard delete.

        Jika model memiliki kolom `deleted_at`, method ini akan mengisi timestamp
        soft delete. Bila tidak ada, object akan dihapus permanen dari database.

        Args:
            obj (Any): Instance model yang akan dihapus.

        Returns:
            bool: True bila operasi delete berhasil dijalankan.

        Example:
            >>> repo.delete(obj=my_model)
        """
        if hasattr(obj, 'deleted_at'):
            obj.deleted_at = now_utc()
            db.session.commit()
        else:
            db.session.delete(obj)
            db.session.commit()
        return True

    def force_delete(self, obj):
        """Menghapus object secara permanen dari database.

        Args:
            obj (Any): Instance model yang akan dihapus permanen.

        Returns:
            bool: True bila operasi hard delete berhasil dijalankan.

        Example:
            >>> repo.force_delete(obj=my_model)
        """
        db.session.delete(obj)
        db.session.commit()
        return True
