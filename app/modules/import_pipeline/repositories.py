"""Repository domain import pipeline form.

Modul ini menyediakan query untuk batch impor form dan row staging impor workbook."""

from app.core.repositories.base import BaseRepository

from .models import ImportBatch, ImportBatchRow


class ImportBatchRepository(BaseRepository):
    """Repository query untuk entity ImportBatch.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = ImportBatchRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = ImportBatchRepository()
        """

        super().__init__(model=ImportBatch)

    def list_by_form(self, form_id):
        """Mengambil submission yang terkait ke form tertentu.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_form(form_id=...)
        """

        return self.model.query.filter(
            ImportBatch.form_id == form_id,
            ImportBatch.deleted_at == None,
        ).order_by(ImportBatch.created_at.desc()).all()


class ImportBatchRowRepository(BaseRepository):
    """Repository query untuk entity ImportBatchRow.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = ImportBatchRowRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = ImportBatchRowRepository()
        """

        super().__init__(model=ImportBatchRow)

    def list_by_batch(self, import_batch_id, limit=None):
        """Mengambil row yang terkait ke satu batch tertentu.

        Args:
            import_batch_id (Any): Primary key internal import batch target.
            limit (Any): Batas jumlah row yang dikembalikan query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_batch(import_batch_id=..., limit=...)
        """

        query = self.model.query.filter(
            ImportBatchRow.import_batch_id == import_batch_id,
            ImportBatchRow.deleted_at == None,
        ).order_by(ImportBatchRow.row_number.asc())
        if limit:
            query = query.limit(limit)
        return query.all()
