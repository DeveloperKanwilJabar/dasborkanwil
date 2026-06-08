"""Model ORM pipeline impor form.

Modul ini menyimpan batch impor submission berbasis workbook Excel dan row staging yang diproses sebelum menjadi submission final."""

import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.extensions import db


class ImportBatch(db.Model):
    """Batch staging untuk upload Excel sebelum data divalidasi dan masuk submissions."""

    __tablename__ = 'import_batches'

    STATUS_UPLOADED = 'uploaded'
    STATUS_MAPPED = 'mapped'
    STATUS_VALIDATING = 'validating'
    STATUS_COMPLETED = 'completed'
    STATUS_COMPLETED_WITH_ERRORS = 'completed_with_errors'
    STATUS_FAILED = 'failed'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    form_id = db.Column('form_id', db.Integer(), db.ForeignKey('forms.id'), nullable=False, index=True)
    form_version_id = db.Column('form_version_id', db.Integer(), db.ForeignKey('form_versions.id'), nullable=False, index=True)

    status = db.Column('status', db.String(30), nullable=False, server_default=STATUS_UPLOADED, index=True)
    original_filename = db.Column('original_filename', db.String(255), nullable=True)

    total_rows = db.Column('total_rows', db.Integer(), nullable=False, server_default='0')
    mapped_rows = db.Column('mapped_rows', db.Integer(), nullable=False, server_default='0')
    valid_rows = db.Column('valid_rows', db.Integer(), nullable=False, server_default='0')
    error_rows = db.Column('error_rows', db.Integer(), nullable=False, server_default='0')
    duplicate_rows = db.Column('duplicate_rows', db.Integer(), nullable=False, server_default='0')

    mapping_config = db.Column('mapping_config', JSONB, nullable=True)
    source_headers = db.Column('source_headers', JSONB, nullable=True)
    meta = db.Column('meta', JSONB, nullable=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)

    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)

    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    form = relationship(
        'Form',
        back_populates='import_batches',
        lazy='joined',
    )

    form_version = relationship(
        'FormVersion',
        back_populates='import_batches',
        lazy='joined',
    )

    rows = relationship(
        'ImportBatchRow',
        back_populates='import_batch',
        lazy='select',
        cascade='save-update, merge',
    )

    __table_args__ = (
        db.Index('ix_import_batches_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<ImportBatch {self.uuid} status={self.status}>"


class ImportBatchRow(db.Model):
    """Row staging hasil mapping Excel sebelum validasi final."""

    __tablename__ = 'import_batch_rows'

    STATUS_PENDING = 'pending'
    STATUS_MAPPED = 'mapped'
    STATUS_VALID = 'valid'
    STATUS_ERROR = 'error'
    STATUS_IMPORTED = 'imported'
    STATUS_SKIPPED = 'skipped'
    STATUS_DUPLICATE = 'duplicate'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    import_batch_id = db.Column('import_batch_id', db.Integer(), db.ForeignKey('import_batches.id'), nullable=False, index=True)
    row_number = db.Column('row_number', db.Integer(), nullable=False)

    raw_payload = db.Column('raw_payload', JSONB, nullable=True)
    mapped_payload = db.Column('mapped_payload', JSONB, nullable=True)
    validation_errors = db.Column('validation_errors', JSONB, nullable=True)

    status = db.Column('status', db.String(30), nullable=False, server_default=STATUS_PENDING, index=True)
    submission_id = db.Column('submission_id', db.Integer(), db.ForeignKey('submissions.id'), nullable=True, index=True)
    row_hash = db.Column('row_hash', db.String(64), nullable=True, index=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    import_batch = relationship(
        'ImportBatch',
        back_populates='rows',
        lazy='joined',
    )

    submission = relationship(
        'Submission',
        lazy='joined',
    )

    __table_args__ = (
        db.UniqueConstraint('import_batch_id', 'row_number', name='uq_import_batch_rows_batch_row_number'),
        db.Index('ix_import_batch_rows_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<ImportBatchRow batch_id={self.import_batch_id} row={self.row_number} status={self.status}>"
