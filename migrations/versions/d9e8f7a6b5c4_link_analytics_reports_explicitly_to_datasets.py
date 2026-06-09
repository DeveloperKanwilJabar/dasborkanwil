"""link analytics reports explicitly to datasets

Revision ID: d9e8f7a6b5c4
Revises: c8f2d3e4a5b6
Create Date: 2026-06-09 15:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9e8f7a6b5c4'
down_revision = 'c8f2d3e4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('analytics_report_definitions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dataset_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_analytics_report_definitions_dataset_id'), ['dataset_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_analytics_report_definitions_dataset_id_analytics_datasets',
            'analytics_datasets',
            ['dataset_id'],
            ['id'],
        )

    with op.batch_alter_table('analytics_report_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dataset_version_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_analytics_report_versions_dataset_version_id'), ['dataset_version_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_analytics_report_versions_dataset_version_id_analytics_dataset_versions',
            'analytics_dataset_versions',
            ['dataset_version_id'],
            ['id'],
        )


def downgrade():
    with op.batch_alter_table('analytics_report_versions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_analytics_report_versions_dataset_version_id_analytics_dataset_versions', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_analytics_report_versions_dataset_version_id'))
        batch_op.drop_column('dataset_version_id')

    with op.batch_alter_table('analytics_report_definitions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_analytics_report_definitions_dataset_id_analytics_datasets', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_analytics_report_definitions_dataset_id'))
        batch_op.drop_column('dataset_id')
