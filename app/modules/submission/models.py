"""Model ORM domain submission.

Modul ini mendefinisikan ReportingPeriod, Submission, dan SubmissionEvent untuk menyimpan jawaban form yang period-aware, lengkap dengan audit event lifecycle submission."""

import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.extensions import db


class ReportingPeriod(db.Model):
    """Dimensi periode pelaporan untuk membatasi dan mengelompokkan submission."""

    __tablename__ = 'reporting_periods'

    PERIOD_TYPE_WEEKLY = 'weekly'
    PERIOD_TYPE_MONTHLY = 'monthly'
    PERIOD_TYPE_QUARTERLY = 'quarterly'
    PERIOD_TYPE_FOUR_MONTHLY = 'four_monthly'
    PERIOD_TYPE_SEMESTER = 'semester'
    PERIOD_TYPE_YEARLY = 'yearly'
    PERIOD_TYPE_FISCAL_YEAR = 'fiscal_year'
    PERIOD_TYPE_REPORTING_BATCH = 'reporting_batch'
    PERIOD_TYPE_INPUT_WINDOW = 'input_window'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    code = db.Column('code', db.String(100), unique=True, nullable=False)
    name = db.Column('name', db.String(255), nullable=False)
    description = db.Column('description', db.Text(), nullable=True)

    period_type = db.Column('period_type', db.String(50), nullable=False, index=True)
    year = db.Column('year', db.Integer(), nullable=False, index=True)

    starts_at = db.Column('starts_at', db.DateTime(timezone=True), nullable=True)
    ends_at = db.Column('ends_at', db.DateTime(timezone=True), nullable=True)
    input_opens_at = db.Column('input_opens_at', db.DateTime(timezone=True), nullable=True)
    input_closes_at = db.Column('input_closes_at', db.DateTime(timezone=True), nullable=True)

    is_active = db.Column('is_active', db.Boolean(), nullable=False, server_default='false', index=True)
    status = db.Column('status', db.String(30), nullable=False, server_default='draft', index=True)
    settings = db.Column('settings', JSONB, nullable=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)

    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)

    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    submissions = relationship(
        'Submission',
        back_populates='reporting_period',
        lazy='select',
        cascade='save-update, merge',
    )

    __table_args__ = (
        db.Index('ix_reporting_periods_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<ReportingPeriod {self.code} - {self.name}>"


class Submission(db.Model):
    """Jawaban/form response yang terikat ke form, versi schema, dan periode pelaporan tertentu."""

    __tablename__ = 'submissions'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    submission_number = db.Column('submission_number', db.String(100), unique=True, nullable=False)

    form_id = db.Column('form_id', db.Integer(), db.ForeignKey('forms.id'), nullable=False, index=True)
    form_version_id = db.Column('form_version_id', db.Integer(), db.ForeignKey('form_versions.id'), nullable=False, index=True)

    reporting_year = db.Column('reporting_year', db.Integer(), nullable=False, index=True)
    reporting_period_id = db.Column(
        'reporting_period_id',
        db.Integer(),
        db.ForeignKey('reporting_periods.id'),
        nullable=True,
        index=True,
    )

    status = db.Column('status', db.String(30), nullable=False, server_default='draft', index=True)
    submitted_at = db.Column('submitted_at', db.DateTime(timezone=True), nullable=True, index=True)

    payload = db.Column('payload', JSONB, nullable=False)
    meta = db.Column('meta', JSONB, nullable=True)
    validation_snapshot = db.Column('validation_snapshot', JSONB, nullable=True)

    submitted_by = db.Column('submitted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True, index=True)
    submitted_by_uuid = db.Column('submitted_by_uuid', db.String(36), nullable=True)

    owner_scope_type = db.Column('owner_scope_type', db.String(50), nullable=False, server_default='global', index=True)
    owner_scope_code = db.Column('owner_scope_code', db.String(100), nullable=True, index=True)
    owner_scope_name = db.Column('owner_scope_name', db.String(255), nullable=True)
    owner_scope_path = db.Column('owner_scope_path', JSONB, nullable=True)

    subject_type = db.Column('subject_type', db.String(50), nullable=True, index=True)
    subject_ref_id = db.Column('subject_ref_id', db.Integer(), nullable=True, index=True)
    subject_ref_uuid = db.Column('subject_ref_uuid', db.String(36), nullable=True, index=True)
    subject_ref_code = db.Column('subject_ref_code', db.String(100), nullable=True, index=True)
    subject_ref_name = db.Column('subject_ref_name', db.String(255), nullable=True)

    access_policy_key = db.Column('access_policy_key', db.String(100), nullable=False, server_default='submission.default', index=True)

    source_type = db.Column('source_type', db.String(50), nullable=True, index=True)
    source_ref = db.Column('source_ref', db.String(255), nullable=True)

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
        back_populates='submissions',
        lazy='joined',
    )

    form_version = relationship(
        'FormVersion',
        back_populates='submissions',
        lazy='joined',
    )

    reporting_period = relationship(
        'ReportingPeriod',
        back_populates='submissions',
        lazy='joined',
    )

    events = relationship(
        'SubmissionEvent',
        back_populates='submission',
        lazy='select',
        cascade='save-update, merge',
    )

    __table_args__ = (
        db.Index('ix_submissions_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<Submission {self.submission_number}>"


class SubmissionEvent(db.Model):
    """Timeline event penting pada lifecycle submission."""

    __tablename__ = 'submission_events'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    submission_id = db.Column('submission_id', db.Integer(), db.ForeignKey('submissions.id'), nullable=False, index=True)

    event_type = db.Column('event_type', db.String(50), nullable=False, index=True)
    event_at = db.Column('event_at', db.DateTime(timezone=True), default=func.now(), nullable=False, index=True)

    actor_user_id = db.Column('actor_user_id', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    actor_user_uuid = db.Column('actor_user_uuid', db.String(36), nullable=True)

    context = db.Column('context', JSONB, nullable=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)

    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)

    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    submission = relationship(
        'Submission',
        back_populates='events',
        lazy='joined',
    )

    __table_args__ = (
        db.Index('ix_submission_events_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        """Menghasilkan representasi string singkat agar object lebih mudah dibaca saat debugging.

        Returns:
            str: Representasi string singkat untuk debugging/logging.

        Example:
            >>> repr(obj)
        """

        return f"<SubmissionEvent submission_id={self.submission_id} event_type={self.event_type}>"
