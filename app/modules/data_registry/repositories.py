"""Repository domain data registry.

Modul ini membungkus query registry, version, record, import batch, dan import row untuk kebutuhan builder, query publik, serta materialisasi."""

from sqlalchemy import func

from app.core.extensions import db
from app.core.repositories.base import BaseRepository

from .models import (
    DataRegistry,
    DataRegistryImportBatch,
    DataRegistryImportRow,
    DataRegistryRecord,
    DataRegistryVersion,
)


class DataRegistryRepository(BaseRepository):
    """Repository query untuk entity DataRegistry.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = DataRegistryRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = DataRegistryRepository()
        """

        super().__init__(model=DataRegistry)

    def get_by_slug(self, slug):
        """Mengambil registry berdasarkan slug bisnis unik.

        Args:
            slug (Any): Business slug unik entity target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_slug(slug=...)
        """

        return self.find_one_by(registry_slug=slug)

    def get_active_by_slug(self, slug):
        """Mengambil registry aktif berdasarkan slug unik.

        Args:
            slug (Any): Business slug unik entity target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_active_by_slug(slug=...)
        """

        return self.model.query.filter(
            DataRegistry.registry_slug == slug,
            DataRegistry.status.in_(['draft', 'published']),
            DataRegistry.deleted_at == None,
        ).first()

    def list_by_status(self, status):
        """Mengambil daftar entity berdasarkan status bisnisnya.

        Args:
            status (Any): Status bisnis yang dipakai untuk filtering data.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_status(status=...)
        """

        return self.find_by(status=status)


class DataRegistryVersionRepository(BaseRepository):
    """Repository query untuk entity DataRegistryVersion.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = DataRegistryVersionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = DataRegistryVersionRepository()
        """

        super().__init__(model=DataRegistryVersion)

    def get_draft_version(self, registry_id):
        """Mengambil draft version aktif untuk entity induk tertentu.

        Args:
            registry_id (Any): Primary key internal registry target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_draft_version(registry_id=...)
        """

        return self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.status == 'draft',
            DataRegistryVersion.deleted_at == None,
        ).order_by(DataRegistryVersion.version_number.desc()).first()

    def get_published_version(self, registry_id):
        """Mengambil version published aktif untuk entity induk tertentu.

        Args:
            registry_id (Any): Primary key internal registry target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_published_version(registry_id=...)
        """

        return self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.status == 'published',
            DataRegistryVersion.deleted_at == None,
        ).order_by(DataRegistryVersion.version_number.desc()).first()

    def get_next_version_number(self, registry_id):
        """Menghitung nomor versi berikutnya untuk entity versioned.

        Args:
            registry_id (Any): Primary key internal registry target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_next_version_number(registry_id=...)
        """

        latest = self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.deleted_at == None,
        ).order_by(DataRegistryVersion.version_number.desc()).first()
        return 1 if not latest else latest.version_number + 1

    def list_versions(self, registry_id, include_deleted=False):
        """Mengambil seluruh versi entity tertentu secara terurut terbaru ke lama.

        Args:
            registry_id (Any): Primary key internal registry target.
            include_deleted (Any): Jika True, record soft delete tetap disertakan dalam hasil query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_versions(registry_id=..., include_deleted=...)
        """

        query = self.model.query.filter(DataRegistryVersion.registry_id == registry_id)
        if not include_deleted:
            query = query.filter(DataRegistryVersion.deleted_at == None)
        return query.order_by(DataRegistryVersion.version_number.desc()).all()

    def archive_published_others(self, registry_id, except_version_id=None):
        """Mengarsipkan version published lain selain target yang dipertahankan.

        Args:
            registry_id (Any): Primary key internal registry target.
            except_version_id (Any): Primary key version yang tidak ikut diubah saat update massal.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo.archive_published_others(registry_id=..., except_version_id=...)
        """

        query = self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.status == 'published',
        )
        if except_version_id is not None:
            query = query.filter(DataRegistryVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.status = 'archived'
        return versions


class DataRegistryRecordRepository(BaseRepository):
    """Repository query untuk entity DataRegistryRecord.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = DataRegistryRecordRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = DataRegistryRecordRepository()
        """

        super().__init__(model=DataRegistryRecord)

    def get_by_key(self, registry_version_id, record_key):
        """Mengambil entity berdasarkan business key unik.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            record_key (Any): Business key record registry.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_key(registry_version_id=..., record_key=...)
        """

        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.record_key == record_key,
            DataRegistryRecord.deleted_at == None,
        ).first()

    def get_by_code(self, registry_version_id, record_code):
        """Mengambil entity berdasarkan business code unik.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            record_code (Any): Business code record registry.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_code(registry_version_id=..., record_code=...)
        """

        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.record_code == record_code,
            DataRegistryRecord.deleted_at == None,
        ).first()

    def list_children(self, registry_version_id, parent_record_id):
        """Mengambil child record langsung dari parent tertentu.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            parent_record_id (Any): Primary key record parent pada registry hierarkis.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_children(registry_version_id=..., parent_record_id=...)
        """

        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.parent_record_id == parent_record_id,
            DataRegistryRecord.deleted_at == None,
        ).order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).all()

    def list_by_level(self, registry_version_id, admin_level, parent_record_id=None):
        """Mengambil record registry berdasarkan level administrasi tertentu.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            admin_level (Any): Level administrasi/level hierarki yang dipakai sebagai filter.
            parent_record_id (Any): Primary key record parent pada registry hierarkis.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_level(registry_version_id=..., admin_level=..., parent_record_id=...)
        """

        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.admin_level == admin_level,
            DataRegistryRecord.deleted_at == None,
        )
        if parent_record_id is not None:
            query = query.filter(DataRegistryRecord.parent_record_id == parent_record_id)
        return query.order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).all()

    def list_options(self, registry_version_id, admin_level=None, parent_record_id=None, q=None, limit=100):
        """Mengambil record registry dalam format ringan untuk komponen pilihan.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            admin_level (Any): Level administrasi/level hierarki yang dipakai sebagai filter.
            parent_record_id (Any): Primary key record parent pada registry hierarkis.
            q (Any): Keyword pencarian bebas untuk option list.
            limit (Any): Batas jumlah row yang dikembalikan query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_options(registry_version_id=..., admin_level=..., parent_record_id=...)
        """

        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.deleted_at == None,
        )
        if admin_level is not None:
            query = query.filter(DataRegistryRecord.admin_level == admin_level)
        if parent_record_id is not None:
            query = query.filter(DataRegistryRecord.parent_record_id == parent_record_id)
        if q:
            query = query.filter(DataRegistryRecord.label.ilike(f'%{q}%'))
        return query.order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).limit(limit).all()

    def list_feature_collection_records(self, registry_version_id, admin_level=None):
        """Mengambil record yang siap dibentuk menjadi feature collection.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            admin_level (Any): Level administrasi/level hierarki yang dipakai sebagai filter.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_feature_collection_records(registry_version_id=..., admin_level=...)
        """

        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.deleted_at == None,
        )
        if admin_level is not None:
            query = query.filter(DataRegistryRecord.admin_level == admin_level)
        return query.order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).all()

    def list_by_registry_version(self, registry_version_id, limit=None):
        """Mengambil data berdasarkan registry version tertentu.

        Args:
            registry_version_id (Any): Primary key internal registry version target.
            limit (Any): Batas jumlah row yang dikembalikan query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_registry_version(registry_version_id=..., limit=...)
        """

        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.deleted_at == None,
        ).order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc(), DataRegistryRecord.id.asc())
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def count_by_registry_version(self, registry_version_id):
        """Menghitung jumlah record dalam satu registry version.

        Args:
            registry_version_id (Any): Primary key internal registry version target.

        Returns:
            int: Jumlah record hasil query.

        Example:
            >>> repo.count_by_registry_version(registry_version_id=...)
        """

        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.deleted_at == None,
        ).count()

    def delete_by_registry_version(self, registry_version_id):
        """Menghapus seluruh record yang terkait ke registry version tertentu.

        Args:
            registry_version_id (Any): Primary key internal registry version target.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo.delete_by_registry_version(registry_version_id=...)
        """

        self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
        ).delete(synchronize_session=False)
        db.session.commit()
        return True


class DataRegistryImportBatchRepository(BaseRepository):
    """Repository query untuk entity DataRegistryImportBatch.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = DataRegistryImportBatchRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = DataRegistryImportBatchRepository()
        """

        super().__init__(model=DataRegistryImportBatch)

    def get_by_id(self, batch_id):
        """Mengambil satu record berdasarkan primary key internal.

        Args:
            batch_id (Any): Primary key internal batch target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_id(batch_id=...)
        """

        return self.model.query.filter(
            DataRegistryImportBatch.id == batch_id,
            DataRegistryImportBatch.deleted_at == None,
        ).first()

    def list_by_registry_version(self, registry_version_id):
        """Mengambil data berdasarkan registry version tertentu.

        Args:
            registry_version_id (Any): Primary key internal registry version target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_registry_version(registry_version_id=...)
        """

        return self.model.query.filter(
            DataRegistryImportBatch.registry_version_id == registry_version_id,
            DataRegistryImportBatch.deleted_at == None,
        ).order_by(DataRegistryImportBatch.created_at.desc(), DataRegistryImportBatch.id.desc()).all()


class DataRegistryImportRowRepository(BaseRepository):
    """Repository query untuk entity DataRegistryImportRow.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = DataRegistryImportRowRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = DataRegistryImportRowRepository()
        """

        super().__init__(model=DataRegistryImportRow)

    def bulk_create(self, rows):
        """Menyimpan banyak row sekaligus ke database.

        Args:
            rows (Any): Kumpulan row model yang akan dipersist massal.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.bulk_create(rows=...)
        """

        if not rows:
            return []

        db.session.add_all(rows)
        db.session.commit()
        return rows

    def list_by_batch(self, import_batch_id, status=None):
        """Mengambil row yang terkait ke satu batch tertentu.

        Args:
            import_batch_id (Any): Primary key internal import batch target.
            status (Any): Status bisnis yang dipakai untuk filtering data.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_batch(import_batch_id=..., status=...)
        """

        query = self.model.query.filter(
            DataRegistryImportRow.import_batch_id == import_batch_id,
            DataRegistryImportRow.deleted_at == None,
        )
        if status is not None:
            query = query.filter(DataRegistryImportRow.status == status)
        return query.order_by(DataRegistryImportRow.row_number.asc(), DataRegistryImportRow.id.asc()).all()

    def count_by_batch_and_status(self, import_batch_id):
        """Menghitung row batch berdasarkan statusnya.

        Args:
            import_batch_id (Any): Primary key internal import batch target.

        Returns:
            int: Jumlah record hasil query.

        Example:
            >>> repo.count_by_batch_and_status(import_batch_id=...)
        """

        rows = db.session.query(
            DataRegistryImportRow.status,
            func.count(DataRegistryImportRow.id),
        ).filter(
            DataRegistryImportRow.import_batch_id == import_batch_id,
            DataRegistryImportRow.deleted_at == None,
        ).group_by(DataRegistryImportRow.status).all()
        return {status: count for status, count in rows}
