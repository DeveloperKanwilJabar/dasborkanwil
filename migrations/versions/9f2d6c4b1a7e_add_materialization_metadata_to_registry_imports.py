"""add materialization metadata to registry imports

Revision ID: 9f2d6c4b1a7e
Revises: 7c5f0183e1c9
Create Date: 2026-05-22 05:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '9f2d6c4b1a7e'
down_revision = '7c5f0183e1c9'
branch_labels = None
depends_on = None


IMPORT_BATCH_STATUS_CHECK = "status IN ('uploaded', 'mapped', 'validating', 'validated', 'materialized', 'failed')"


def upgrade():
    with op.batch_alter_table('data_registry_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('materialized_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                'materialization_metadata',
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            )
        )

    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_status_valid', type_='check')
        batch_op.add_column(sa.Column('materialized_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('materialized_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('materialized_by_uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                'materialization_summary',
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            )
        )
        batch_op.create_foreign_key(
            'fk_data_registry_import_batches_materialized_by_users',
            'users',
            ['materialized_by'],
            ['id'],
        )
        batch_op.create_check_constraint('ck_data_registry_import_batches_status_valid', IMPORT_BATCH_STATUS_CHECK)


def downgrade():
    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_status_valid', type_='check')
        batch_op.drop_constraint('fk_data_registry_import_batches_materialized_by_users', type_='foreignkey')
        batch_op.drop_column('materialization_summary')
        batch_op.drop_column('materialized_by_uuid')
        batch_op.drop_column('materialized_by')
        batch_op.drop_column('materialized_at')
        batch_op.create_check_constraint(
            'ck_data_registry_import_batches_status_valid',
            "status IN ('uploaded', 'mapped', 'validating', 'validated', 'failed')",
        )

    with op.batch_alter_table('data_registry_versions', schema=None) as batch_op:
        batch_op.drop_column('materialization_metadata')
        batch_op.drop_column('materialized_at')
