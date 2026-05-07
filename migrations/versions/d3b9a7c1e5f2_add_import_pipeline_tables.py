"""add import pipeline tables

Revision ID: d3b9a7c1e5f2
Revises: 7d61714f1651
Create Date: 2026-05-08 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd3b9a7c1e5f2'
down_revision = '7d61714f1651'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('form_version_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='uploaded', nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('total_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('mapped_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('valid_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duplicate_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('mapping_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id']),
        sa.ForeignKeyConstraint(['form_version_id'], ['form_versions.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    with op.batch_alter_table('import_batches', schema=None) as batch_op:
        batch_op.create_index('ix_import_batches_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batches_form_id'), ['form_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batches_form_version_id'), ['form_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batches_status'), ['status'], unique=False)

    op.create_table(
        'import_batch_rows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('import_batch_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mapped_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=True),
        sa.Column('row_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id']),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('import_batch_id', 'row_number', name='uq_import_batch_rows_batch_row_number'),
        sa.UniqueConstraint('uuid'),
    )
    with op.batch_alter_table('import_batch_rows', schema=None) as batch_op:
        batch_op.create_index('ix_import_batch_rows_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batch_rows_import_batch_id'), ['import_batch_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batch_rows_row_hash'), ['row_hash'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batch_rows_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_import_batch_rows_submission_id'), ['submission_id'], unique=False)


def downgrade():
    with op.batch_alter_table('import_batch_rows', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_import_batch_rows_submission_id'))
        batch_op.drop_index(batch_op.f('ix_import_batch_rows_status'))
        batch_op.drop_index(batch_op.f('ix_import_batch_rows_row_hash'))
        batch_op.drop_index(batch_op.f('ix_import_batch_rows_import_batch_id'))
        batch_op.drop_index('ix_import_batch_rows_deleted_at')

    op.drop_table('import_batch_rows')

    with op.batch_alter_table('import_batches', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_import_batches_status'))
        batch_op.drop_index(batch_op.f('ix_import_batches_form_version_id'))
        batch_op.drop_index(batch_op.f('ix_import_batches_form_id'))
        batch_op.drop_index('ix_import_batches_deleted_at')

    op.drop_table('import_batches')
