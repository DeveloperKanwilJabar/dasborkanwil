from app.core.repositories.base import BaseRepository

from .models import ImportBatch, ImportBatchRow


class ImportBatchRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=ImportBatch)

    def list_by_form(self, form_id):
        return self.model.query.filter(
            ImportBatch.form_id == form_id,
            ImportBatch.deleted_at == None,
        ).order_by(ImportBatch.created_at.desc()).all()


class ImportBatchRowRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=ImportBatchRow)

    def list_by_batch(self, import_batch_id, limit=None):
        query = self.model.query.filter(
            ImportBatchRow.import_batch_id == import_batch_id,
            ImportBatchRow.deleted_at == None,
        ).order_by(ImportBatchRow.row_number.asc())
        if limit:
            query = query.limit(limit)
        return query.all()
