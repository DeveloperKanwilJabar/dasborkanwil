"""allow manual_entry batch type for data registry imports

Revision ID: e5f6a7b8c9d0
Revises: c4d7a9e2b1f0
Create Date: 2026-05-26 18:35:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'c4d7a9e2b1f0'
branch_labels = None
depends_on = None


LEGACY_IMPORT_BATCH_TYPE_CHECK = "batch_type IN ('file_upload', 'manual_seed', 'sync_snapshot')"
UPDATED_IMPORT_BATCH_TYPE_CHECK = "batch_type IN ('file_upload', 'manual_seed', 'manual_entry', 'sync_snapshot')"


def upgrade():
    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_batch_type_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_import_batches_batch_type_valid',
            UPDATED_IMPORT_BATCH_TYPE_CHECK,
        )



def downgrade():
    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_batch_type_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_import_batches_batch_type_valid',
            LEGACY_IMPORT_BATCH_TYPE_CHECK,
        )
