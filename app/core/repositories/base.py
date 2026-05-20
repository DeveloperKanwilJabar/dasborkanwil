from app.core.extensions import db
from sqlalchemy import desc
from app.core.utils import now_utc

class BaseRepository:
    def __init__(self, model):
        self.model = model

    def get_all(self, include_deleted=False):
        """Ambil semua data. Secara default menyembunyikan yang di-soft delete."""
        query = self.model.query
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.all()

    def get_by_id(self, id):
        """Ambil data berdasarkan ID."""
        return self.model.query.get(id)

    def count(self, include_deleted=False):
        """Menghitung total record."""
        query = self.model.query
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.count()

    def find_by(self, include_deleted=False, **filters):
        """
        Mencari data berdasarkan kriteria dinamis.
         - include_deleted: Jika True, maka hasil akan menyertakan data yang sudah di-soft delete (deleted_at != None).
         - **filters: Kriteria pencarian dinamis yang diteruskan ke filter_by SQLAlchemy.
        Contoh penggunaan di service:
            - self.repository.find_by(active=True, role='admin') -> mencari semua data yang aktif. Return list dan bisa kosong.
        """
        query = self.model.query.filter_by(**filters)
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.all()

    def find_one_by(self, include_deleted=False, **filters):
        """
        Mencari satu data (Return Object atau None).
        Sangat cocok untuk field unik seperti NIP, Email, UUID.
        Contoh penggunaan di service:
            - self.repository.find_one_by(nip="some-nip") -> mencari berdasarkan NIP dan return object atau None
        """
        query = self.model.query.filter_by(**filters)
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.first()

    def paginate(self, page=1, per_page=10, include_deleted=False, order_by_desc=True):
        """Mekanisme pagination standar Flask-SQLAlchemy."""
        query = self.model.query

        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)

        if order_by_desc and hasattr(self.model, 'created_at'):
            query = query.order_by(desc(self.model.created_at))

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def save(self, obj):
        db.session.add(obj)
        db.session.commit()
        return obj

    def delete(self, obj):
        """Soft delete jika kolomnya ada, jika tidak maka hard delete."""
        if hasattr(obj, 'deleted_at'):
            obj.deleted_at = now_utc()
            db.session.commit()
        else:
            db.session.delete(obj)
            db.session.commit()
        return True

    def force_delete(self, obj):
        """Benar-benar menghapus dari database."""
        db.session.delete(obj)
        db.session.commit()
        return True
