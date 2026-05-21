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
