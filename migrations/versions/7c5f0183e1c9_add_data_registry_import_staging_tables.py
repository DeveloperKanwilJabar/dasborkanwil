"""add data registry import staging tables

Revision ID: 7c5f0183e1c9
Revises: c6fdf0d1a8a1
Create Date: 2026-05-22 03:38:27.175019

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7c5f0183e1c9'
down_revision = 'c6fdf0d1a8a1'
branch_labels = None
depends_on = None


IMPORT_BATCH_TYPE_CHECK = "batch_type IN ('file_upload', 'manual_seed', 'sync_snapshot')"
IMPORT_BATCH_STATUS_CHECK = "status IN ('uploaded', 'mapped', 'validating', 'validated', 'failed')"
IMPORT_ROW_STATUS_CHECK = "status IN ('pending', 'mapped', 'valid', 'error', 'duplicate', 'skipped')"


def upgrade():
    op.create_table(
        'data_registry_import_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('registry_id', sa.Integer(), nullable=False),
        sa.Column('registry_version_id', sa.Integer(), nullable=False),
        sa.Column('batch_type', sa.String(length=50), server_default='file_upload', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='uploaded', nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=255), nullable=True),
        sa.Column('reporting_year', sa.Integer(), nullable=True),
        sa.Column('total_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('mapped_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('valid_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duplicate_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('skipped_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('mapping_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('source_headers', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('source_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('validation_summary', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
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
        sa.ForeignKeyConstraint(['registry_version_id'], ['data_registry_versions.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_data_registry_import_batches_batch_type'), ['batch_type'], unique=False)
        batch_op.create_index('ix_data_registry_import_batches_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_batches_registry_id'), ['registry_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_batches_registry_version_id'), ['registry_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_batches_reporting_year'), ['reporting_year'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_batches_status'), ['status'], unique=False)
        batch_op.create_check_constraint('ck_data_registry_import_batches_batch_type_valid', IMPORT_BATCH_TYPE_CHECK)
        batch_op.create_check_constraint('ck_data_registry_import_batches_status_valid', IMPORT_BATCH_STATUS_CHECK)

    op.create_table(
        'data_registry_import_rows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('import_batch_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('row_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('record_key_candidate', sa.String(length=255), nullable=True),
        sa.Column('record_code_candidate', sa.String(length=100), nullable=True),
        sa.Column('duplicate_of_row_id', sa.Integer(), nullable=True),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('mapped_payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('normalized_payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('validation_warnings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('lineage_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['duplicate_of_row_id'], ['data_registry_import_rows.id']),
        sa.ForeignKeyConstraint(['import_batch_id'], ['data_registry_import_batches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_batch_id', 'row_number', name='uq_data_registry_import_rows_import_batch_id_row_number'),
        sa.UniqueConstraint('uuid'),
    )
    with op.batch_alter_table('data_registry_import_rows', schema=None) as batch_op:
        batch_op.create_index('ix_data_registry_import_rows_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_rows_duplicate_of_row_id'), ['duplicate_of_row_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_rows_import_batch_id'), ['import_batch_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_rows_row_hash'), ['row_hash'], unique=False)
        batch_op.create_index(batch_op.f('ix_data_registry_import_rows_status'), ['status'], unique=False)
        batch_op.create_check_constraint('ck_data_registry_import_rows_status_valid', IMPORT_ROW_STATUS_CHECK)


def downgrade():
    with op.batch_alter_table('data_registry_import_rows', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_rows_status_valid', type_='check')
        batch_op.drop_index(batch_op.f('ix_data_registry_import_rows_status'))
        batch_op.drop_index(batch_op.f('ix_data_registry_import_rows_row_hash'))
        batch_op.drop_index(batch_op.f('ix_data_registry_import_rows_import_batch_id'))
        batch_op.drop_index(batch_op.f('ix_data_registry_import_rows_duplicate_of_row_id'))
        batch_op.drop_index('ix_data_registry_import_rows_deleted_at')

    op.drop_table('data_registry_import_rows')

    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_status_valid', type_='check')
        batch_op.drop_constraint('ck_data_registry_import_batches_batch_type_valid', type_='check')
        batch_op.drop_index(batch_op.f('ix_data_registry_import_batches_status'))
        batch_op.drop_index(batch_op.f('ix_data_registry_import_batches_reporting_year'))
        batch_op.drop_index(batch_op.f('ix_data_registry_import_batches_registry_version_id'))
        batch_op.drop_index(batch_op.f('ix_data_registry_import_batches_registry_id'))
        batch_op.drop_index('ix_data_registry_import_batches_deleted_at')
        batch_op.drop_index(batch_op.f('ix_data_registry_import_batches_batch_type'))

    op.drop_table('data_registry_import_batches')
