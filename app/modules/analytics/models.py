import uuid

from sqlalchemy import ForeignKeyConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.extensions import db


class AnalyticsDataset(db.Model):
    """Identitas dataset analitik lintas versi kontrak dan histori run."""

    __tablename__ = 'analytics_datasets'

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'

    SOURCE_DOMAIN_SUBMISSION = 'submission'
    SOURCE_DOMAIN_DATA_REGISTRY = 'data_registry'
    SOURCE_DOMAIN_HYBRID = 'hybrid'

    SOURCE_TYPE_SUBMISSION_FACT = 'submission_fact'
    SOURCE_TYPE_PUBLISHED_REGISTRY_DIMENSION = 'published_registry_dimension'
    SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT = 'aggregated_submission_fact'
    SOURCE_TYPE_HYBRID_FACT_DIMENSION = 'hybrid_fact_dimension'

    REPORTING_YEAR_MODE_ACTIVE = 'active_year'
    REPORTING_YEAR_MODE_EXPLICIT = 'explicit'
    REPORTING_YEAR_MODE_ALL_TIME = 'all_time'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    dataset_key = db.Column('dataset_key', db.String(150), unique=True, nullable=False)
    name = db.Column('name', db.String(255), nullable=False)
    description = db.Column('description', db.Text(), nullable=True)

    source_domain = db.Column('source_domain', db.String(50), nullable=False, server_default=STATUS_DRAFT.replace('draft', 'submission'), index=True)
    source_type = db.Column('source_type', db.String(80), nullable=False, server_default=SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT, index=True)
    primary_source_ref = db.Column('primary_source_ref', db.String(255), nullable=True)

    status = db.Column('status', db.String(30), nullable=False, server_default=STATUS_DRAFT, index=True)
    is_active = db.Column('is_active', db.Boolean(), nullable=False, server_default='true', index=True)
    is_year_scoped = db.Column('is_year_scoped', db.Boolean(), nullable=False, server_default='true', index=True)
    default_reporting_year_mode = db.Column(
        'default_reporting_year_mode',
        db.String(30),
        nullable=False,
        server_default=REPORTING_YEAR_MODE_ACTIVE,
        index=True,
    )

    owner_scope_type = db.Column('owner_scope_type', db.String(50), nullable=True)
    owner_scope_code = db.Column('owner_scope_code', db.String(100), nullable=True, index=True)
    owner_scope_name = db.Column('owner_scope_name', db.String(255), nullable=True)
    owner_scope_path = db.Column('owner_scope_path', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    settings_json = db.Column('settings_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    tags_json = db.Column('tags_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

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
        'AnalyticsDatasetVersion',
        back_populates='dataset',
        lazy='select',
        cascade='save-update, merge',
    )

    runs = relationship(
        'AnalyticsDatasetRun',
        back_populates='dataset',
        lazy='select',
        cascade='save-update, merge',
        overlaps='dataset_version,runs',
    )

    __table_args__ = (
        db.Index('ix_analytics_datasets_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        return f"<AnalyticsDataset {self.dataset_key}>"


class AnalyticsDatasetVersion(db.Model):
    """Resep versi dataset: source contract, transform, output schema, dan freshness policy."""

    __tablename__ = 'analytics_dataset_versions'

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'

    GRAIN_PER_SUBMISSION = 'per_submission'
    GRAIN_PER_FORM_PER_YEAR = 'per_form_per_year'
    GRAIN_PER_SCOPE_PER_YEAR = 'per_scope_per_year'
    GRAIN_PER_REGISTRY_RECORD_PER_YEAR = 'per_registry_record_per_year'

    FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT = 'submissions.submitted_at'
    FRESHNESS_SOURCE_DATA_REGISTRY_MATERIALIZED_AT = 'data_registry_versions.materialized_at'
    FRESHNESS_SOURCE_HYBRID_WATERMARK = 'hybrid_watermark'

    FRESHNESS_STRATEGY_MAX_TIMESTAMP = 'max_timestamp'
    FRESHNESS_STRATEGY_SOURCE_WATERMARK_COMPARE = 'source_watermark_compare'
    FRESHNESS_STRATEGY_MANUAL_ASSERTION = 'manual_assertion'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    dataset_id = db.Column('dataset_id', db.Integer(), db.ForeignKey('analytics_datasets.id'), nullable=False, index=True)
    version_number = db.Column('version_number', db.Integer(), nullable=False)

    status = db.Column('status', db.String(30), nullable=False, server_default=STATUS_DRAFT, index=True)
    is_current_draft = db.Column('is_current_draft', db.Boolean(), nullable=False, server_default='true', index=True)
    is_current_published = db.Column('is_current_published', db.Boolean(), nullable=False, server_default='false', index=True)

    source_contract_json = db.Column('source_contract_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    query_spec_json = db.Column('query_spec_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    transform_spec_json = db.Column('transform_spec_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    join_registry_spec_json = db.Column('join_registry_spec_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    grain_key = db.Column('grain_key', db.String(60), nullable=False, index=True)
    output_schema_json = db.Column('output_schema_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    dimension_definitions_json = db.Column('dimension_definitions_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    metric_definitions_json = db.Column('metric_definitions_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    default_filters_json = db.Column('default_filters_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    sort_spec_json = db.Column('sort_spec_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    freshness_source_type = db.Column('freshness_source_type', db.String(80), nullable=False, index=True)
    freshness_source_ref = db.Column('freshness_source_ref', db.String(255), nullable=True)
    freshness_strategy = db.Column('freshness_strategy', db.String(50), nullable=False, index=True)
    freshness_policy_json = db.Column('freshness_policy_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    publish_notes = db.Column('publish_notes', db.Text(), nullable=True)
    published_at = db.Column('published_at', db.DateTime(timezone=True), nullable=True, index=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)
    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)
    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    dataset = relationship(
        'AnalyticsDataset',
        back_populates='versions',
        lazy='joined',
    )

    runs = relationship(
        'AnalyticsDatasetRun',
        back_populates='dataset_version',
        lazy='select',
        cascade='save-update, merge',
        overlaps='dataset,runs',
    )

    __table_args__ = (
        db.UniqueConstraint('dataset_id', 'version_number', name='uq_analytics_dataset_versions_dataset_id_version_number'),
        db.UniqueConstraint('id', 'dataset_id', name='uq_analytics_dataset_versions_id_dataset_id'),
        db.Index('ix_analytics_dataset_versions_deleted_at', 'deleted_at'),
        db.Index(
            'ux_analytics_dataset_versions_one_current_draft_per_dataset',
            'dataset_id',
            unique=True,
            postgresql_where=text('is_current_draft = true AND deleted_at IS NULL'),
            sqlite_where=text('is_current_draft = 1 AND deleted_at IS NULL'),
        ),
        db.Index(
            'ux_analytics_dataset_versions_one_current_published_per_dataset',
            'dataset_id',
            unique=True,
            postgresql_where=text('is_current_published = true AND deleted_at IS NULL'),
            sqlite_where=text('is_current_published = 1 AND deleted_at IS NULL'),
        ),
    )

    def __repr__(self):
        return f"<AnalyticsDatasetVersion dataset_id={self.dataset_id} version={self.version_number}>"


class AnalyticsDatasetRun(db.Model):
    """Histori eksekusi refresh untuk satu versi dataset tertentu."""

    __tablename__ = 'analytics_dataset_runs'

    TRIGGER_MANUAL = 'manual'
    TRIGGER_PREVIEW = 'preview'
    TRIGGER_PUBLISH_HOOK = 'publish_hook'
    TRIGGER_CRON = 'cron'
    TRIGGER_SYSTEM = 'system'

    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    FRESHNESS_UNKNOWN = 'unknown'
    FRESHNESS_FRESH = 'fresh'
    FRESHNESS_STALE = 'stale'
    FRESHNESS_FAILED = 'failed'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    dataset_id = db.Column('dataset_id', db.Integer(), db.ForeignKey('analytics_datasets.id'), nullable=False, index=True)
    dataset_version_id = db.Column('dataset_version_id', db.Integer(), nullable=False, index=True)

    run_key = db.Column('run_key', db.String(255), unique=True, nullable=False)
    trigger_type = db.Column('trigger_type', db.String(30), nullable=False, index=True)
    trigger_ref = db.Column('trigger_ref', db.String(255), nullable=True)

    requested_reporting_year = db.Column('requested_reporting_year', db.Integer(), nullable=True, index=True)
    requested_reporting_period_id = db.Column(
        'requested_reporting_period_id',
        db.Integer(),
        db.ForeignKey('reporting_periods.id'),
        nullable=True,
        index=True,
    )
    requested_filters_json = db.Column('requested_filters_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    status = db.Column('status', db.String(30), nullable=False, server_default=STATUS_QUEUED, index=True)
    started_at = db.Column('started_at', db.DateTime(timezone=True), nullable=True, index=True)
    finished_at = db.Column('finished_at', db.DateTime(timezone=True), nullable=True, index=True)
    duration_ms = db.Column('duration_ms', db.BigInteger(), nullable=True)

    source_watermark = db.Column('source_watermark', db.String(255), nullable=True)
    freshness_status = db.Column('freshness_status', db.String(30), nullable=False, server_default=FRESHNESS_UNKNOWN, index=True)
    source_snapshot_json = db.Column('source_snapshot_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    freshness_evaluated_at = db.Column('freshness_evaluated_at', db.DateTime(timezone=True), nullable=True)

    result_row_count = db.Column('result_row_count', db.BigInteger(), nullable=True)
    result_schema_json = db.Column('result_schema_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    result_preview_json = db.Column('result_preview_json', JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    materialization_ref = db.Column('materialization_ref', db.String(255), nullable=True, index=True)
    summary_json = db.Column('summary_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    error_code = db.Column('error_code', db.String(100), nullable=True)
    error_message = db.Column('error_message', db.Text(), nullable=True)
    error_detail_json = db.Column('error_detail_json', JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)
    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)
    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    dataset = relationship(
        'AnalyticsDataset',
        back_populates='runs',
        lazy='joined',
        overlaps='dataset_version,runs',
    )
    dataset_version = relationship(
        'AnalyticsDatasetVersion',
        back_populates='runs',
        lazy='joined',
        primaryjoin='and_(AnalyticsDatasetRun.dataset_version_id == AnalyticsDatasetVersion.id, AnalyticsDatasetRun.dataset_id == AnalyticsDatasetVersion.dataset_id)',
        foreign_keys='[AnalyticsDatasetRun.dataset_version_id, AnalyticsDatasetRun.dataset_id]',
        overlaps='dataset,runs',
    )
    requested_reporting_period = relationship(
        'ReportingPeriod',
        lazy='joined',
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['dataset_version_id', 'dataset_id'],
            ['analytics_dataset_versions.id', 'analytics_dataset_versions.dataset_id'],
            name='fk_analytics_dataset_runs_dataset_version_id_dataset_id',
        ),
        db.Index('ix_analytics_dataset_runs_deleted_at', 'deleted_at'),
    )

    def __repr__(self):
        return f"<AnalyticsDatasetRun {self.run_key}>"
