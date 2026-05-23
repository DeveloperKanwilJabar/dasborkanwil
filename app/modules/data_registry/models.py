import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.extensions import db


class DataRegistry(db.Model):
    __tablename__ = 'data_registries'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    registry_slug = db.Column('registry_slug', db.String(191), unique=True, nullable=False)
    registry_code = db.Column('registry_code', db.String(100), unique=True, nullable=True)
    name = db.Column('name', db.String(255), nullable=False)
    description = db.Column('description', db.Text(), nullable=True)

    registry_type = db.Column('registry_type', db.String(50), nullable=False, server_default='geo', index=True)
    category_key = db.Column('category_key', db.String(100), nullable=False, server_default='wilayah', index=True)
    source_mode = db.Column('source_mode', db.String(50), nullable=False, server_default='import_file', index=True)
    data_shape = db.Column('data_shape', db.String(50), nullable=False, server_default='hierarchical_geo', index=True)
    is_year_scoped = db.Column('is_year_scoped', db.Boolean(), nullable=False, server_default='false')
    status = db.Column('status', db.String(50), nullable=False, server_default='draft', index=True)
    schema_meta = db.Column('schema_meta', JSONB, nullable=False, server_default='{}')

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)
    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)
    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    versions = relationship('DataRegistryVersion', back_populates='registry', lazy='select', cascade='save-update, merge')
    import_batches = relationship('DataRegistryImportBatch', back_populates='registry', lazy='select', cascade='save-update, merge')
    records = relationship('DataRegistryRecord', back_populates='registry', lazy='select', cascade='save-update, merge')

    __table_args__ = (
        db.Index('ix_data_registries_deleted_at', 'deleted_at'),
    )


class DataRegistryVersion(db.Model):
    __tablename__ = 'data_registry_versions'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    registry_id = db.Column('registry_id', db.Integer(), db.ForeignKey('data_registries.id'), nullable=False, index=True)
    version_number = db.Column('version_number', db.Integer(), nullable=False)
    status = db.Column('status', db.String(50), nullable=False, server_default='draft', index=True)

    schema_json = db.Column('schema_json', JSONB, nullable=False, server_default='{}')
    mapping_spec = db.Column('mapping_spec', JSONB, nullable=False, server_default='{}')
    source_snapshot = db.Column('source_snapshot', JSONB, nullable=False, server_default='{}')
    publish_notes = db.Column('publish_notes', db.Text(), nullable=True)
    published_at = db.Column('published_at', db.DateTime(timezone=True), nullable=True)
    materialized_at = db.Column('materialized_at', db.DateTime(timezone=True), nullable=True)
    materialization_metadata = db.Column('materialization_metadata', JSONB, nullable=False, server_default='{}')
    source_watermark = db.Column('source_watermark', db.String(255), nullable=True)
    materialized_watermark = db.Column('materialized_watermark', db.String(255), nullable=True)
    freshness_status = db.Column('freshness_status', db.String(50), nullable=False, server_default='unknown', index=True)
    freshness_signature = db.Column('freshness_signature', db.String(255), nullable=True)

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)
    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)
    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    registry = relationship('DataRegistry', back_populates='versions', lazy='joined')
    import_batches = relationship('DataRegistryImportBatch', back_populates='registry_version', lazy='select', cascade='save-update, merge')
    records = relationship('DataRegistryRecord', back_populates='registry_version', lazy='select', cascade='save-update, merge')

    __table_args__ = (
        db.UniqueConstraint('registry_id', 'version_number', name='uq_data_registry_versions_registry_id_version_number'),
        db.Index('ix_data_registry_versions_deleted_at', 'deleted_at'),
    )


class DataRegistryRecord(db.Model):
    __tablename__ = 'data_registry_records'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    registry_id = db.Column('registry_id', db.Integer(), db.ForeignKey('data_registries.id'), nullable=False, index=True)
    registry_version_id = db.Column('registry_version_id', db.Integer(), db.ForeignKey('data_registry_versions.id'), nullable=False, index=True)
    parent_record_id = db.Column('parent_record_id', db.Integer(), db.ForeignKey('data_registry_records.id'), nullable=True, index=True)

    record_key = db.Column('record_key', db.String(255), nullable=False)
    record_code = db.Column('record_code', db.String(100), nullable=False)
    external_code = db.Column('external_code', db.String(100), nullable=True)
    label = db.Column('label', db.String(255), nullable=False)
    display_label = db.Column('display_label', db.String(255), nullable=True)
    normalized_label = db.Column('normalized_label', db.String(255), nullable=False)

    admin_level = db.Column('admin_level', db.String(50), nullable=False, index=True)
    admin_level_code = db.Column('admin_level_code', db.String(20), nullable=False, index=True)
    city_regency_kind = db.Column('city_regency_kind', db.String(50), nullable=True, index=True)
    province_code = db.Column('province_code', db.String(100), nullable=True, index=True)
    city_regency_code = db.Column('city_regency_code', db.String(100), nullable=True, index=True)
    district_code = db.Column('district_code', db.String(100), nullable=True, index=True)
    village_code = db.Column('village_code', db.String(100), nullable=True, index=True)
    village_adm_status = db.Column('village_adm_status', db.String(50), nullable=True, index=True)

    sort_order = db.Column('sort_order', db.Integer(), nullable=True)
    is_active = db.Column('is_active', db.Boolean(), nullable=False, server_default='true', index=True)
    valid_from = db.Column('valid_from', db.Date(), nullable=True)
    valid_to = db.Column('valid_to', db.Date(), nullable=True)

    centroid_lat = db.Column('centroid_lat', db.Numeric(10, 6), nullable=True)
    centroid_lng = db.Column('centroid_lng', db.Numeric(10, 6), nullable=True)
    bbox_min_lat = db.Column('bbox_min_lat', db.Numeric(10, 6), nullable=True)
    bbox_min_lng = db.Column('bbox_min_lng', db.Numeric(10, 6), nullable=True)
    bbox_max_lat = db.Column('bbox_max_lat', db.Numeric(10, 6), nullable=True)
    bbox_max_lng = db.Column('bbox_max_lng', db.Numeric(10, 6), nullable=True)
    geometry_json = db.Column('geometry_json', JSONB, nullable=True)

    source_row_number = db.Column('source_row_number', db.Integer(), nullable=True)
    source_row_hash = db.Column('source_row_hash', db.String(255), nullable=True)
    source_snapshot = db.Column('source_snapshot', JSONB, nullable=False, server_default='{}')
    payload = db.Column('payload', JSONB, nullable=False, server_default='{}')

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)
    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)
    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    registry = relationship('DataRegistry', back_populates='records', lazy='joined')
    registry_version = relationship('DataRegistryVersion', back_populates='records', lazy='joined')
    parent = relationship('DataRegistryRecord', remote_side='DataRegistryRecord.id', back_populates='children', lazy='joined')
    children = relationship('DataRegistryRecord', back_populates='parent', lazy='select', cascade='save-update, merge')

    __table_args__ = (
        db.UniqueConstraint('registry_version_id', 'record_key', name='uq_data_registry_records_registry_version_id_record_key'),
        db.UniqueConstraint('registry_version_id', 'record_code', name='uq_data_registry_records_registry_version_id_record_code'),
        db.Index('ix_data_registry_records_deleted_at', 'deleted_at'),
    )


class DataRegistryImportBatch(db.Model):
    __tablename__ = 'data_registry_import_batches'

    STATUS_UPLOADED = 'uploaded'
    STATUS_MAPPED = 'mapped'
    STATUS_VALIDATING = 'validating'
    STATUS_VALIDATED = 'validated'
    STATUS_MATERIALIZED = 'materialized'
    STATUS_FAILED = 'failed'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    registry_id = db.Column('registry_id', db.Integer(), db.ForeignKey('data_registries.id'), nullable=False, index=True)
    registry_version_id = db.Column('registry_version_id', db.Integer(), db.ForeignKey('data_registry_versions.id'), nullable=False, index=True)

    batch_type = db.Column('batch_type', db.String(50), nullable=False, server_default='file_upload', index=True)
    status = db.Column('status', db.String(50), nullable=False, server_default=STATUS_UPLOADED, index=True)
    original_filename = db.Column('original_filename', db.String(255), nullable=True)
    mime_type = db.Column('mime_type', db.String(255), nullable=True)
    reporting_year = db.Column('reporting_year', db.Integer(), nullable=True, index=True)

    total_rows = db.Column('total_rows', db.Integer(), nullable=False, server_default='0')
    mapped_rows = db.Column('mapped_rows', db.Integer(), nullable=False, server_default='0')
    valid_rows = db.Column('valid_rows', db.Integer(), nullable=False, server_default='0')
    error_rows = db.Column('error_rows', db.Integer(), nullable=False, server_default='0')
    duplicate_rows = db.Column('duplicate_rows', db.Integer(), nullable=False, server_default='0')
    skipped_rows = db.Column('skipped_rows', db.Integer(), nullable=False, server_default='0')

    mapping_snapshot = db.Column('mapping_snapshot', JSONB, nullable=False, server_default='{}')
    source_headers = db.Column('source_headers', JSONB, nullable=False, server_default='[]')
    source_snapshot = db.Column('source_snapshot', JSONB, nullable=False, server_default='{}')
    validation_summary = db.Column('validation_summary', JSONB, nullable=False, server_default='{}')
    materialized_at = db.Column('materialized_at', db.DateTime(timezone=True), nullable=True)
    materialized_by = db.Column('materialized_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    materialized_by_uuid = db.Column('materialized_by_uuid', db.String(36), nullable=True)
    materialization_summary = db.Column('materialization_summary', JSONB, nullable=False, server_default='{}')

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    created_by = db.Column('created_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    created_by_uuid = db.Column('created_by_uuid', db.String(36), nullable=True)
    updated_by = db.Column('updated_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    updated_by_uuid = db.Column('updated_by_uuid', db.String(36), nullable=True)
    deleted_by = db.Column('deleted_by', db.Integer(), db.ForeignKey('users.id'), nullable=True)
    deleted_by_uuid = db.Column('deleted_by_uuid', db.String(36), nullable=True)

    registry = relationship('DataRegistry', back_populates='import_batches', lazy='joined')
    registry_version = relationship('DataRegistryVersion', back_populates='import_batches', lazy='joined')
    rows = relationship('DataRegistryImportRow', back_populates='batch', lazy='select', cascade='save-update, merge')

    __table_args__ = (
        db.Index('ix_data_registry_import_batches_deleted_at', 'deleted_at'),
    )


class DataRegistryImportRow(db.Model):
    __tablename__ = 'data_registry_import_rows'

    STATUS_PENDING = 'pending'
    STATUS_MAPPED = 'mapped'
    STATUS_VALID = 'valid'
    STATUS_ERROR = 'error'
    STATUS_DUPLICATE = 'duplicate'
    STATUS_SKIPPED = 'skipped'

    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    import_batch_id = db.Column('import_batch_id', db.Integer(), db.ForeignKey('data_registry_import_batches.id'), nullable=False, index=True)
    row_number = db.Column('row_number', db.Integer(), nullable=False)
    row_hash = db.Column('row_hash', db.String(64), nullable=True, index=True)
    status = db.Column('status', db.String(50), nullable=False, server_default=STATUS_PENDING, index=True)

    record_key_candidate = db.Column('record_key_candidate', db.String(255), nullable=True)
    record_code_candidate = db.Column('record_code_candidate', db.String(100), nullable=True)
    duplicate_of_row_id = db.Column('duplicate_of_row_id', db.Integer(), db.ForeignKey('data_registry_import_rows.id'), nullable=True, index=True)

    raw_payload = db.Column('raw_payload', JSONB, nullable=False, server_default='{}')
    mapped_payload = db.Column('mapped_payload', JSONB, nullable=False, server_default='{}')
    normalized_payload = db.Column('normalized_payload', JSONB, nullable=False, server_default='{}')
    validation_errors = db.Column('validation_errors', JSONB, nullable=False, server_default='{}')
    validation_warnings = db.Column('validation_warnings', JSONB, nullable=False, server_default='{}')
    lineage_snapshot = db.Column('lineage_snapshot', JSONB, nullable=False, server_default='{}')

    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    batch = relationship('DataRegistryImportBatch', back_populates='rows', lazy='joined')
    duplicate_of_row = relationship('DataRegistryImportRow', remote_side='DataRegistryImportRow.id', lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('import_batch_id', 'row_number', name='uq_data_registry_import_rows_import_batch_id_row_number'),
        db.Index('ix_data_registry_import_rows_deleted_at', 'deleted_at'),
    )
