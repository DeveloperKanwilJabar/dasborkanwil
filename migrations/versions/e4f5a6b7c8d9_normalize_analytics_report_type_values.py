"""normalize analytics report type values

Revision ID: e4f5a6b7c8d9
Revises: d9e8f7a6b5c4
Create Date: 2026-06-10 11:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f5a6b7c8d9'
down_revision = 'd9e8f7a6b5c4'
branch_labels = None
depends_on = None


OLD_REPORT_TYPE_CHECK = "report_type IN ('pk', 'renaksi', 'scorecard', 'monitoring', 'custom')"


def upgrade():
    op.execute(
        sa.text(
            """
            UPDATE analytics_report_definitions
            SET report_type = CASE report_type
                WHEN 'custom_report' THEN 'custom'
                WHEN 'performance_report' THEN 'scorecard'
                WHEN 'narrative_report' THEN 'monitoring'
                WHEN 'geo_report' THEN 'monitoring'
                ELSE report_type
            END
            WHERE report_type IN ('custom_report', 'performance_report', 'narrative_report', 'geo_report')
            """
        )
    )

    with op.batch_alter_table('analytics_report_definitions', schema=None) as batch_op:
        batch_op.drop_constraint('ck_analytics_report_definitions_report_type_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_analytics_report_definitions_report_type_valid',
            OLD_REPORT_TYPE_CHECK,
        )


def downgrade():
    with op.batch_alter_table('analytics_report_definitions', schema=None) as batch_op:
        batch_op.drop_constraint('ck_analytics_report_definitions_report_type_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_analytics_report_definitions_report_type_valid',
            OLD_REPORT_TYPE_CHECK,
        )
