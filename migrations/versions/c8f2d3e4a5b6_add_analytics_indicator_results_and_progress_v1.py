"""add analytics indicator results and progress v1

Revision ID: c8f2d3e4a5b6
Revises: b7e1c2d3f4a5
Create Date: 2026-06-04 12:05:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c8f2d3e4a5b6'
down_revision = 'b7e1c2d3f4a5'
branch_labels = None
depends_on = None


ANALYTICS_INDICATOR_RESULT_STATUS_CHECK = "status IN ('draft', 'published', 'failed')"
ANALYTICS_COMPLETION_STATUS_CHECK = "completion_status IN ('not_started', 'in_progress', 'completed')"
ANALYTICS_PROGRESS_ENTRY_STATUS_CHECK = "status IN ('draft', 'in_progress', 'completed')"
ANALYTICS_PROGRESS_ITEM_STATUS_CHECK = "status IN ('pending', 'in_progress', 'done', 'blocked')"


JSONB_EMPTY_OBJECT = sa.text("'{}'::jsonb")


def upgrade():
    op.create_table(
        'analytics_indicator_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('indicator_version_id', sa.Integer(), nullable=False),
        sa.Column('dataset_run_id', sa.Integer(), nullable=True),
        sa.Column('reporting_year', sa.Integer(), nullable=True),
        sa.Column('reporting_period_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('completion_status', sa.String(length=30), nullable=False, server_default='not_started'),
        sa.Column('measured_value', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('target_value', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('achievement_percentage', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('qualitative_summary', sa.Text(), nullable=True),
        sa.Column('constraint_notes', sa.Text(), nullable=True),
        sa.Column('narrative_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('source_snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['indicator_version_id'], ['analytics_indicator_versions.id']),
        sa.ForeignKeyConstraint(['dataset_run_id'], ['analytics_dataset_runs.id']),
        sa.ForeignKeyConstraint(['reporting_period_id'], ['reporting_periods.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_indicator_results_uuid'),
    )
    with op.batch_alter_table('analytics_indicator_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_indicator_version_id'), ['indicator_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_dataset_run_id'), ['dataset_run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_reporting_year'), ['reporting_year'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_reporting_period_id'), ['reporting_period_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_completion_status'), ['completion_status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_results_calculated_at'), ['calculated_at'], unique=False)
        batch_op.create_index('ix_analytics_indicator_results_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_indicator_results_status_valid', ANALYTICS_INDICATOR_RESULT_STATUS_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_results_completion_status_valid', ANALYTICS_COMPLETION_STATUS_CHECK)

    op.create_table(
        'analytics_indicator_progress_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('indicator_version_id', sa.Integer(), nullable=False),
        sa.Column('reporting_year', sa.Integer(), nullable=True),
        sa.Column('reporting_period_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('progress_percent', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('qualitative_summary', sa.Text(), nullable=True),
        sa.Column('constraint_notes', sa.Text(), nullable=True),
        sa.Column('narrative_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['indicator_version_id'], ['analytics_indicator_versions.id']),
        sa.ForeignKeyConstraint(['reporting_period_id'], ['reporting_periods.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_indicator_progress_entries_uuid'),
    )
    with op.batch_alter_table('analytics_indicator_progress_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_indicator_progress_entries_indicator_version_id'), ['indicator_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_progress_entries_reporting_year'), ['reporting_year'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_progress_entries_reporting_period_id'), ['reporting_period_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_progress_entries_status'), ['status'], unique=False)
        batch_op.create_index('ix_analytics_indicator_progress_entries_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_indicator_progress_entries_status_valid', ANALYTICS_PROGRESS_ENTRY_STATUS_CHECK)

    op.create_table(
        'analytics_indicator_progress_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('progress_entry_id', sa.Integer(), nullable=False),
        sa.Column('item_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('narrative_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['progress_entry_id'], ['analytics_indicator_progress_entries.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_indicator_progress_items_uuid'),
    )
    with op.batch_alter_table('analytics_indicator_progress_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_indicator_progress_items_progress_entry_id'), ['progress_entry_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_progress_items_status'), ['status'], unique=False)
        batch_op.create_index('ix_analytics_indicator_progress_items_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_indicator_progress_items_status_valid', ANALYTICS_PROGRESS_ITEM_STATUS_CHECK)


def downgrade():
    op.drop_table('analytics_indicator_progress_items')
    op.drop_table('analytics_indicator_progress_entries')
    op.drop_table('analytics_indicator_results')
