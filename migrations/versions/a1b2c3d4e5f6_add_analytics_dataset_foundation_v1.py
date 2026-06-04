"""add analytics dataset foundation v1

Revision ID: a1b2c3d4e5f6
Revises: c4d7a9e2b1f0
Create Date: 2026-06-03 12:10:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'c4d7a9e2b1f0'
branch_labels = None
depends_on = None


ANALYTICS_DATASET_STATUS_CHECK = "status IN ('draft', 'active', 'archived')"
ANALYTICS_SOURCE_DOMAIN_CHECK = "source_domain IN ('submission', 'data_registry', 'hybrid')"
ANALYTICS_SOURCE_TYPE_CHECK = (
    "source_type IN ('submission_fact', 'published_registry_dimension', 'aggregated_submission_fact', 'hybrid_fact_dimension')"
)
ANALYTICS_DEFAULT_REPORTING_YEAR_MODE_CHECK = (
    "default_reporting_year_mode IN ('active_year', 'explicit', 'all_time')"
)
ANALYTICS_DATASET_VERSION_STATUS_CHECK = "status IN ('draft', 'published', 'archived')"
ANALYTICS_GRAIN_KEY_CHECK = (
    "grain_key IN ('per_submission', 'per_form_per_year', 'per_scope_per_year', 'per_registry_record_per_year')"
)
ANALYTICS_FRESHNESS_SOURCE_TYPE_CHECK = (
    "freshness_source_type IN ('submissions.submitted_at', 'data_registry_versions.materialized_at', 'hybrid_watermark')"
)
ANALYTICS_FRESHNESS_STRATEGY_CHECK = (
    "freshness_strategy IN ('max_timestamp', 'source_watermark_compare', 'manual_assertion')"
)
ANALYTICS_DATASET_VERSION_STATE_CHECK = (
    "NOT (is_current_draft = true AND is_current_published = true)"
)
ANALYTICS_DATASET_VERSION_PUBLISH_STATE_CHECK = (
    "(is_current_published = false) OR (status = 'published')"
)
ANALYTICS_DATASET_VERSION_PUBLISHED_AT_CHECK = (
    "(published_at IS NULL) OR (status IN ('published', 'archived'))"
)
ANALYTICS_RUN_TRIGGER_TYPE_CHECK = "trigger_type IN ('manual', 'preview', 'publish_hook', 'cron', 'system')"
ANALYTICS_RUN_STATUS_CHECK = "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')"
ANALYTICS_FRESHNESS_STATUS_CHECK = "freshness_status IN ('unknown', 'fresh', 'stale', 'failed')"
ANALYTICS_RUN_DURATION_NON_NEGATIVE_CHECK = "(duration_ms IS NULL) OR (duration_ms >= 0)"
ANALYTICS_RUN_FINISHED_AFTER_STARTED_CHECK = (
    "(started_at IS NULL OR finished_at IS NULL OR finished_at >= started_at)"
)
ANALYTICS_RUN_SUCCEEDED_STARTED_AT_CHECK = "(status != 'succeeded') OR (started_at IS NOT NULL)"
ANALYTICS_RUN_FAILED_ERROR_MESSAGE_CHECK = "(status != 'failed') OR (error_message IS NOT NULL)"


JSONB_EMPTY_OBJECT = sa.text("'{}'::jsonb")
JSONB_EMPTY_ARRAY = sa.text("'[]'::jsonb")


def upgrade():
    op.create_table(
        'analytics_datasets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('dataset_key', sa.String(length=150), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_domain', sa.String(length=50), nullable=False, server_default='submission'),
        sa.Column('source_type', sa.String(length=80), nullable=False, server_default='aggregated_submission_fact'),
        sa.Column('primary_source_ref', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_year_scoped', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('default_reporting_year_mode', sa.String(length=30), nullable=False, server_default='active_year'),
        sa.Column('owner_scope_type', sa.String(length=50), nullable=True),
        sa.Column('owner_scope_code', sa.String(length=100), nullable=True),
        sa.Column('owner_scope_name', sa.String(length=255), nullable=True),
        sa.Column('owner_scope_path', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('settings_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('tags_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_datasets_uuid'),
        sa.UniqueConstraint('dataset_key', name='uq_analytics_datasets_dataset_key'),
    )
    with op.batch_alter_table('analytics_datasets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_datasets_source_domain'), ['source_domain'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_datasets_source_type'), ['source_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_datasets_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_datasets_is_active'), ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_datasets_is_year_scoped'), ['is_year_scoped'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_datasets_default_reporting_year_mode'), ['default_reporting_year_mode'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_datasets_owner_scope_code'), ['owner_scope_code'], unique=False)
        batch_op.create_index('ix_analytics_datasets_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_datasets_status_valid', ANALYTICS_DATASET_STATUS_CHECK)
        batch_op.create_check_constraint('ck_analytics_datasets_source_domain_valid', ANALYTICS_SOURCE_DOMAIN_CHECK)
        batch_op.create_check_constraint('ck_analytics_datasets_source_type_valid', ANALYTICS_SOURCE_TYPE_CHECK)
        batch_op.create_check_constraint(
            'ck_analytics_datasets_default_reporting_year_mode_valid',
            ANALYTICS_DEFAULT_REPORTING_YEAR_MODE_CHECK,
        )

    op.create_table(
        'analytics_dataset_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('is_current_draft', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_current_published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('source_contract_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('query_spec_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('transform_spec_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('join_registry_spec_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('grain_key', sa.String(length=60), nullable=False),
        sa.Column('output_schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('dimension_definitions_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('metric_definitions_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('default_filters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('sort_spec_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('freshness_source_type', sa.String(length=80), nullable=False),
        sa.Column('freshness_source_ref', sa.String(length=255), nullable=True),
        sa.Column('freshness_strategy', sa.String(length=50), nullable=False),
        sa.Column('freshness_policy_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('publish_notes', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['analytics_datasets.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_dataset_versions_uuid'),
        sa.UniqueConstraint('dataset_id', 'version_number', name='uq_analytics_dataset_versions_dataset_id_version_number'),
        sa.UniqueConstraint('id', 'dataset_id', name='uq_analytics_dataset_versions_id_dataset_id'),
    )
    with op.batch_alter_table('analytics_dataset_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_dataset_id'), ['dataset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_is_current_draft'), ['is_current_draft'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_is_current_published'), ['is_current_published'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_grain_key'), ['grain_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_freshness_source_type'), ['freshness_source_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_freshness_strategy'), ['freshness_strategy'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_versions_published_at'), ['published_at'], unique=False)
        batch_op.create_index('ix_analytics_dataset_versions_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_dataset_versions_status_valid', ANALYTICS_DATASET_VERSION_STATUS_CHECK)
        batch_op.create_check_constraint('ck_analytics_dataset_versions_grain_key_valid', ANALYTICS_GRAIN_KEY_CHECK)
        batch_op.create_check_constraint(
            'ck_analytics_dataset_versions_freshness_source_type_valid',
            ANALYTICS_FRESHNESS_SOURCE_TYPE_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_versions_freshness_strategy_valid',
            ANALYTICS_FRESHNESS_STRATEGY_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_versions_state_valid',
            ANALYTICS_DATASET_VERSION_STATE_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_versions_publish_state_valid',
            ANALYTICS_DATASET_VERSION_PUBLISH_STATE_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_versions_published_at_valid',
            ANALYTICS_DATASET_VERSION_PUBLISHED_AT_CHECK,
        )

    op.create_index(
        'ux_analytics_dataset_versions_one_current_draft_per_dataset',
        'analytics_dataset_versions',
        ['dataset_id'],
        unique=True,
        postgresql_where=sa.text('is_current_draft = true AND deleted_at IS NULL'),
    )
    op.create_index(
        'ux_analytics_dataset_versions_one_current_published_per_dataset',
        'analytics_dataset_versions',
        ['dataset_id'],
        unique=True,
        postgresql_where=sa.text('is_current_published = true AND deleted_at IS NULL'),
    )

    op.create_table(
        'analytics_dataset_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('dataset_version_id', sa.Integer(), nullable=False),
        sa.Column('run_key', sa.String(length=255), nullable=False),
        sa.Column('trigger_type', sa.String(length=30), nullable=False),
        sa.Column('trigger_ref', sa.String(length=255), nullable=True),
        sa.Column('requested_reporting_year', sa.Integer(), nullable=True),
        sa.Column('requested_reporting_period_id', sa.Integer(), nullable=True),
        sa.Column('requested_filters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='queued'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('source_watermark', sa.String(length=255), nullable=True),
        sa.Column('freshness_status', sa.String(length=30), nullable=False, server_default='unknown'),
        sa.Column('source_snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('freshness_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_row_count', sa.BigInteger(), nullable=True),
        sa.Column('result_schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('result_preview_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
        sa.Column('materialization_ref', sa.String(length=255), nullable=True),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_detail_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['analytics_datasets.id']),
        sa.ForeignKeyConstraint(['requested_reporting_period_id'], ['reporting_periods.id']),
        sa.ForeignKeyConstraint(
            ['dataset_version_id', 'dataset_id'],
            ['analytics_dataset_versions.id', 'analytics_dataset_versions.dataset_id'],
            name='fk_analytics_dataset_runs_dataset_version_id_dataset_id',
        ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_dataset_runs_uuid'),
        sa.UniqueConstraint('run_key', name='uq_analytics_dataset_runs_run_key'),
    )
    with op.batch_alter_table('analytics_dataset_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_dataset_id'), ['dataset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_dataset_version_id'), ['dataset_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_trigger_type'), ['trigger_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_started_at'), ['started_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_finished_at'), ['finished_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_requested_reporting_year'), ['requested_reporting_year'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_requested_reporting_period_id'), ['requested_reporting_period_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_freshness_status'), ['freshness_status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_dataset_runs_materialization_ref'), ['materialization_ref'], unique=False)
        batch_op.create_index('ix_analytics_dataset_runs_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_dataset_runs_trigger_type_valid', ANALYTICS_RUN_TRIGGER_TYPE_CHECK)
        batch_op.create_check_constraint('ck_analytics_dataset_runs_status_valid', ANALYTICS_RUN_STATUS_CHECK)
        batch_op.create_check_constraint('ck_analytics_dataset_runs_freshness_status_valid', ANALYTICS_FRESHNESS_STATUS_CHECK)
        batch_op.create_check_constraint(
            'ck_analytics_dataset_runs_duration_non_negative',
            ANALYTICS_RUN_DURATION_NON_NEGATIVE_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_runs_finished_after_started',
            ANALYTICS_RUN_FINISHED_AFTER_STARTED_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_runs_succeeded_started_at_valid',
            ANALYTICS_RUN_SUCCEEDED_STARTED_AT_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_analytics_dataset_runs_failed_error_message_valid',
            ANALYTICS_RUN_FAILED_ERROR_MESSAGE_CHECK,
        )


def downgrade():
    op.drop_table('analytics_dataset_runs')
    op.drop_index('ux_analytics_dataset_versions_one_current_published_per_dataset', table_name='analytics_dataset_versions')
    op.drop_index('ux_analytics_dataset_versions_one_current_draft_per_dataset', table_name='analytics_dataset_versions')
    op.drop_table('analytics_dataset_versions')
    op.drop_table('analytics_datasets')
