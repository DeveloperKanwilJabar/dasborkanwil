"""add data registry wilayah v1

Revision ID: c6fdf0d1a8a1
Revises: d3b9a7c1e5f2
Create Date: 2026-05-21 12:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c6fdf0d1a8a1'
down_revision = 'd3b9a7c1e5f2'
branch_labels = None
depends_on = None


REGISTRY_STATUS_CHECK = "status IN ('draft', 'published', 'archived')"
REGISTRY_TYPE_CHECK = "registry_type IN ('geo')"
REGISTRY_SOURCE_MODE_CHECK = "source_mode IN ('manual', 'import_file', 'sync_external')"
REGISTRY_DATA_SHAPE_CHECK = "data_shape IN ('hierarchical_geo', 'geojson')"
VERSION_FRESHNESS_STATUS_CHECK = "freshness_status IN ('unknown', 'fresh', 'stale', 'refreshing', 'failed')"
RECORD_ADMIN_LEVEL_CHECK = "admin_level IN ('province', 'city_regency', 'district', 'village')"
RECORD_CITY_REGENCY_KIND_CHECK = "city_regency_kind IS NULL OR city_regency_kind IN ('kabupaten', 'kota')"
RECORD_VILLAGE_ADM_STATUS_CHECK = "village_adm_status IS NULL OR village_adm_status IN ('desa', 'kelurahan')"
RECORD_VALID_RANGE_CHECK = "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from"
RECORD_LAT_RANGE_CHECK = "centroid_lat IS NULL OR (centroid_lat >= -90 AND centroid_lat <= 90)"
RECORD_LNG_RANGE_CHECK = "centroid_lng IS NULL OR (centroid_lng >= -180 AND centroid_lng <= 180)"
RECORD_BBOX_MIN_LAT_RANGE_CHECK = "bbox_min_lat IS NULL OR (bbox_min_lat >= -90 AND bbox_min_lat <= 90)"
RECORD_BBOX_MAX_LAT_RANGE_CHECK = "bbox_max_lat IS NULL OR (bbox_max_lat >= -90 AND bbox_max_lat <= 90)"
RECORD_BBOX_MIN_LNG_RANGE_CHECK = "bbox_min_lng IS NULL OR (bbox_min_lng >= -180 AND bbox_min_lng <= 180)"
RECORD_BBOX_MAX_LNG_RANGE_CHECK = "bbox_max_lng IS NULL OR (bbox_max_lng >= -180 AND bbox_max_lng <= 180)"


def upgrade():
    op.create_table(
        'data_registries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('registry_slug', sa.String(length=191), nullable=False),
        sa.Column('registry_code', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('registry_type', sa.String(length=50), server_default='geo', nullable=False),
        sa.Column('category_key', sa.String(length=100), server_default='wilayah', nullable=False),
        sa.Column('source_mode', sa.String(length=50), server_default='import_file', nullable=False),
        sa.Column('data_shape', sa.String(length=50), server_default='hierarchical_geo', nullable=False),
        sa.Column('is_year_scoped', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='draft', nullable=False),
        sa.Column('schema_meta', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('registry_slug'),
        sa.UniqueConstraint('registry_code'),
    )
    with op.batch_alter_table('data_registries', schema=None) as batch_op:
        batch_op.create_index('ix_data_registries_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registries_registry_type'), ['registry_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registries_category_key'), ['category_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registries_source_mode'), ['source_mode'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registries_data_shape'), ['data_shape'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registries_is_year_scoped'), ['is_year_scoped'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registries_status'), ['status'], unique=False)
        batch_op.create_check_constraint('ck_data_registries_status_valid', REGISTRY_STATUS_CHECK)
        batch_op.create_check_constraint('ck_data_registries_registry_type_valid', REGISTRY_TYPE_CHECK)
        batch_op.create_check_constraint('ck_data_registries_source_mode_valid', REGISTRY_SOURCE_MODE_CHECK)
        batch_op.create_check_constraint('ck_data_registries_data_shape_valid', REGISTRY_DATA_SHAPE_CHECK)

    op.create_table(
        'data_registry_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('registry_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='draft', nullable=False),
        sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('mapping_spec', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('source_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('publish_notes', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_watermark', sa.String(length=255), nullable=True),
        sa.Column('materialized_watermark', sa.String(length=255), nullable=True),
        sa.Column('freshness_status', sa.String(length=50), server_default='unknown', nullable=False),
        sa.Column('freshness_signature', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['registry_id'], ['data_registries.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('registry_id', 'version_number', name='uq_data_registry_versions_registry_id_version_number'),
    )
    with op.batch_alter_table('data_registry_versions', schema=None) as batch_op:
        batch_op.create_index('ix_data_registry_versions_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_versions_registry_id'), ['registry_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_versions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_versions_freshness_status'), ['freshness_status'], unique=False)
        batch_op.create_check_constraint('ck_data_registry_versions_status_valid', REGISTRY_STATUS_CHECK)
        batch_op.create_check_constraint('ck_data_registry_versions_freshness_status_valid', VERSION_FRESHNESS_STATUS_CHECK)
    op.create_index(
        'ux_data_registry_versions_one_published_per_registry',
        'data_registry_versions',
        ['registry_id'],
        unique=True,
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )

    op.create_table(
        'data_registry_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('registry_id', sa.Integer(), nullable=False),
        sa.Column('registry_version_id', sa.Integer(), nullable=False),
        sa.Column('parent_record_id', sa.Integer(), nullable=True),
        sa.Column('record_key', sa.String(length=255), nullable=False),
        sa.Column('record_code', sa.String(length=100), nullable=False),
        sa.Column('external_code', sa.String(length=100), nullable=True),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('display_label', sa.String(length=255), nullable=True),
        sa.Column('normalized_label', sa.String(length=255), nullable=False),
        sa.Column('admin_level', sa.String(length=50), nullable=False),
        sa.Column('admin_level_code', sa.String(length=20), nullable=False),
        sa.Column('city_regency_kind', sa.String(length=50), nullable=True),
        sa.Column('province_code', sa.String(length=100), nullable=True),
        sa.Column('city_regency_code', sa.String(length=100), nullable=True),
        sa.Column('district_code', sa.String(length=100), nullable=True),
        sa.Column('village_code', sa.String(length=100), nullable=True),
        sa.Column('village_adm_status', sa.String(length=50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('centroid_lat', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('centroid_lng', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('bbox_min_lat', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('bbox_min_lng', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('bbox_max_lat', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('bbox_max_lng', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('geometry_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_row_number', sa.Integer(), nullable=True),
        sa.Column('source_row_hash', sa.String(length=255), nullable=True),
        sa.Column('source_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['parent_record_id'], ['data_registry_records.id']),
        sa.ForeignKeyConstraint(['registry_id'], ['data_registries.id']),
        sa.ForeignKeyConstraint(['registry_version_id'], ['data_registry_versions.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('registry_version_id', 'record_key', name='uq_data_registry_records_registry_version_id_record_key'),
        sa.UniqueConstraint('registry_version_id', 'record_code', name='uq_data_registry_records_registry_version_id_record_code'),
    )
    with op.batch_alter_table('data_registry_records', schema=None) as batch_op:
        batch_op.create_index('ix_data_registry_records_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_registry_id'), ['registry_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_registry_version_id'), ['registry_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_parent_record_id'), ['parent_record_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_admin_level'), ['admin_level'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_admin_level_code'), ['admin_level_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_city_regency_kind'), ['city_regency_kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_province_code'), ['province_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_city_regency_code'), ['city_regency_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_district_code'), ['district_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_village_code'), ['village_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_village_adm_status'), ['village_adm_status'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_records_is_active'), ['is_active'], unique=False)
        batch_op.create_check_constraint('ck_data_registry_records_admin_level_valid', RECORD_ADMIN_LEVEL_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_city_regency_kind_valid', RECORD_CITY_REGENCY_KIND_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_village_adm_status_valid', RECORD_VILLAGE_ADM_STATUS_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_valid_range', RECORD_VALID_RANGE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_centroid_lat_range', RECORD_LAT_RANGE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_centroid_lng_range', RECORD_LNG_RANGE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_bbox_min_lat_range', RECORD_BBOX_MIN_LAT_RANGE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_bbox_max_lat_range', RECORD_BBOX_MAX_LAT_RANGE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_bbox_min_lng_range', RECORD_BBOX_MIN_LNG_RANGE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_records_bbox_max_lng_range', RECORD_BBOX_MAX_LNG_RANGE_CHECK)
    op.create_index(
        'ux_data_registry_records_registry_version_id_external_code',
        'data_registry_records',
        ['registry_version_id', 'external_code'],
        unique=True,
        postgresql_where=sa.text('external_code IS NOT NULL AND deleted_at IS NULL'),
    )


def downgrade():
    op.drop_index('ux_data_registry_records_registry_version_id_external_code', table_name='data_registry_records')
    with op.batch_alter_table('data_registry_records', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_records_bbox_max_lng_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_bbox_min_lng_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_bbox_max_lat_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_bbox_min_lat_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_centroid_lng_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_centroid_lat_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_valid_range', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_village_adm_status_valid', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_city_regency_kind_valid', type_='check')
        batch_op.drop_constraint('ck_data_registry_records_admin_level_valid', type_='check')
        batch_op.drop_index(batch_op.f('ix_data_registry_records_is_active'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_village_adm_status'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_village_code'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_district_code'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_city_regency_code'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_province_code'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_city_regency_kind'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_admin_level_code'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_admin_level'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_parent_record_id'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_registry_version_id'))
        batch_op.drop_index(batch_op.f('ix_data_registry_records_registry_id'))
        batch_op.drop_index('ix_data_registry_records_deleted_at')
    op.drop_table('data_registry_records')

    op.drop_index('ux_data_registry_versions_one_published_per_registry', table_name='data_registry_versions')
    with op.batch_alter_table('data_registry_versions', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_versions_freshness_status_valid', type_='check')
        batch_op.drop_constraint('ck_data_registry_versions_status_valid', type_='check')
        batch_op.drop_index(batch_op.f('ix_data_registry_versions_freshness_status'))
        batch_op.drop_index(batch_op.f('ix_data_registry_versions_status'))
        batch_op.drop_index(batch_op.f('ix_data_registry_versions_registry_id'))
        batch_op.drop_index('ix_data_registry_versions_deleted_at')
    op.drop_table('data_registry_versions')

    with op.batch_alter_table('data_registries', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registries_data_shape_valid', type_='check')
        batch_op.drop_constraint('ck_data_registries_source_mode_valid', type_='check')
        batch_op.drop_constraint('ck_data_registries_registry_type_valid', type_='check')
        batch_op.drop_constraint('ck_data_registries_status_valid', type_='check')
        batch_op.drop_index(batch_op.f('ix_data_registries_status'))
        batch_op.drop_index(batch_op.f('ix_data_registries_is_year_scoped'))
        batch_op.drop_index(batch_op.f('ix_data_registries_data_shape'))
        batch_op.drop_index(batch_op.f('ix_data_registries_source_mode'))
        batch_op.drop_index(batch_op.f('ix_data_registries_category_key'))
        batch_op.drop_index(batch_op.f('ix_data_registries_registry_type'))
        batch_op.drop_index('ix_data_registries_deleted_at')
    op.drop_table('data_registries')
