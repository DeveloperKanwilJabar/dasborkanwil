"""Model ORM domain form.

Modul ini mendefinisikan entity inti Form dan FormVersion sebagai fondasi registri form dinamis, versioning schema, serta relasinya ke submission dan import batch."""

import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.extensions import db


class Form(db.Model):
    """Business identity untuk form lintas versi schema."""

    __tablename__ = 'forms'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    code = db.Column('code', db.String(100), unique=True, nullable=False)
    slug = db.Column('slug', db.String(150), unique=True, nullable=False)
    name = db.Column('name', db.String(255), nullable=False)
    description = db.Column('description', db.Text(), nullable=True)

    status = db.Column('status', db.String(30), nullable=False, server_default='draft', index=True)
    visibility = db.Column('visibility', db.String(30), nullable=False, server_default='internal', index=True)

    settings = db.Column('settings', JSONB, nullable=True)

    owner_user_id = db.Column('owner_user_id', db.Integer(), db.ForeignKey('users.id'), nullable=True, index=True)
    owner_scope_type = db.Column('owner_scope_type', db.String(50), nullable=False, server_default='global', index=True)
    owner_scope_code = db.Column('owner_scope_code', db.String(100), nullable=True, index=True)
    owner_scope_name = db.Column('owner_scope_name', db.String(255), nullable=True)
    owner_scope_path = db.Column('owner_scope_path', JSONB, nullable=True)
    target_scope_type = db.Column('target_scope_type', db.String(50), nullable=False, server_default='global', index=True)
    target_scope_code = db.Column('target_scope_code', db.String(100), nullable=True, index=True)
    target_scope_name = db.Column('target_scope_name', db.String(255), nullable=True)
    target_scope_path = db.Column('target_scope_path', JSONB, nullable=True)
    access_policy_key = db.Column('access_policy_key', db.String(100), nullable=False, server_default='form.default', index=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)

    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)

    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    versions = relationship(
        'FormVersion',
        back_populates='form',
        lazy='select',
        cascade='save-update, merge',
    )

    submissions = relationship(
        'Submission',
        back_populates='form',
        lazy='select',
        cascade='save-update, merge',
    )

    import_batches = relationship(
        'ImportBatch',
        back_populates='form',
        lazy='select',
        cascade='save-update, merge',
    )

    __table_args__ = (
        db.Index('ix_forms_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<Form {self.code} - {self.name}>"


class FormVersion(db.Model):
    """Snapshot schema form per versi yang menjadi acuan submission."""

    __tablename__ = 'form_versions'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    form_id = db.Column('form_id', db.Integer(), db.ForeignKey('forms.id'), nullable=False, index=True)

    version_number = db.Column('version_number', db.Integer(), nullable=False)
    version_label = db.Column('version_label', db.String(100), nullable=True)

    schema = db.Column('schema', JSONB, nullable=False)
    validation_rules = db.Column('validation_rules', JSONB, nullable=True)
    submission_contract = db.Column('submission_contract', JSONB, nullable=True)
    scope_snapshot = db.Column('scope_snapshot', JSONB, nullable=True)
    access_policy_snapshot = db.Column('access_policy_snapshot', JSONB, nullable=True)

    status = db.Column('status', db.String(30), nullable=False, server_default='draft', index=True)
    is_published = db.Column('is_published', db.Boolean(), nullable=False, server_default='false', index=True)
    published_at = db.Column('published_at', db.DateTime(timezone=True), nullable=True)

    notes = db.Column('notes', db.Text(), nullable=True)

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
        back_populates='versions',
        lazy='joined',
    )

    submissions = relationship(
        'Submission',
        back_populates='form_version',
        lazy='select',
        cascade='save-update, merge',
    )

    import_batches = relationship(
        'ImportBatch',
        back_populates='form_version',
        lazy='select',
        cascade='save-update, merge',
    )

    __table_args__ = (
        db.UniqueConstraint('form_id', 'version_number', name='uq_form_versions_form_id_version_number'),
        db.Index('ix_form_versions_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<FormVersion form_id={self.form_id} version={self.version_number}>"
