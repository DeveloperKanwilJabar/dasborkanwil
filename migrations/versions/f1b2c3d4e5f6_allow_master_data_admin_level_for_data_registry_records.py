"""allow master_data admin level for data registry records

Revision ID: f1b2c3d4e5f6
Revises: e5f6a7b8c9d0
Create Date: 2026-06-01 11:58:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f1b2c3d4e5f6'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


LEGACY_RECORD_ADMIN_LEVEL_CHECK = "admin_level IN ('province', 'city_regency', 'district', 'village')"
UPDATED_RECORD_ADMIN_LEVEL_CHECK = (
    "admin_level IN ('province', 'city_regency', 'district', 'village', 'master_data')"
)


def upgrade():
    with op.batch_alter_table('data_registry_records', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_records_admin_level_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_records_admin_level_valid',
            UPDATED_RECORD_ADMIN_LEVEL_CHECK,
        )


def downgrade():
    with op.batch_alter_table('data_registry_records', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_records_admin_level_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_records_admin_level_valid',
            LEGACY_RECORD_ADMIN_LEVEL_CHECK,
        )
