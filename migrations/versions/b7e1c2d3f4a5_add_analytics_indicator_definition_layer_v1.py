"""add analytics indicator definition layer v1

Revision ID: b7e1c2d3f4a5
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04 11:55:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b7e1c2d3f4a5'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


ANALYTICS_REPORT_TYPE_CHECK = "report_type IN ('pk', 'renaksi', 'scorecard', 'monitoring', 'custom')"
ANALYTICS_DEFINITION_STATUS_CHECK = "status IN ('draft', 'active', 'archived')"
ANALYTICS_VERSION_STATUS_CHECK = "status IN ('draft', 'published', 'archived')"
ANALYTICS_INDICATOR_SOURCE_MODE_CHECK = "source_mode IN ('dataset_driven', 'manual_input', 'hybrid')"
ANALYTICS_INDICATOR_CALCULATION_TYPE_CHECK = (
    "calculation_type IN ('absolute_count', 'percentage', 'ratio', 'score', 'weighted_score', 'checklist_completion', 'boolean_completion', 'custom_formula')"
)
ANALYTICS_INDICATOR_TARGET_SOURCE_TYPE_CHECK = (
    "target_source_type IN ('manual_central_target', 'manual_local_target', 'derived_from_dataset', 'derived_from_manual_input', 'hybrid')"
)
ANALYTICS_PERIOD_MODE_CHECK = "period_mode IN ('quarterly', 'semester', 'yearly', 'multi_period')"
ANALYTICS_AGGREGATION_STRATEGY_CHECK = (
    "aggregation_strategy IN ('sum', 'avg', 'last_value', 'max', 'custom_formula')"
)
ANALYTICS_VERSION_STATE_CHECK = "NOT (is_current_draft = true AND is_current_published = true)"
ANALYTICS_VERSION_PUBLISH_STATE_CHECK = "(is_current_published = false) OR (status = 'published')"
ANALYTICS_VERSION_PUBLISHED_AT_CHECK = "(published_at IS NULL) OR (status IN ('published', 'archived'))"


JSONB_EMPTY_OBJECT = sa.text("'{}'::jsonb")
JSONB_EMPTY_ARRAY = sa.text("'[]'::jsonb")


def upgrade():
    op.create_table(
        'analytics_report_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('report_key', sa.String(length=150), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(length=50), nullable=False, server_default='custom'),
        sa.Column('category_key', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
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
        sa.UniqueConstraint('uuid', name='uq_analytics_report_definitions_uuid'),
        sa.UniqueConstraint('report_key', name='uq_analytics_report_definitions_report_key'),
    )
    with op.batch_alter_table('analytics_report_definitions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_report_definitions_report_type'), ['report_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_definitions_category_key'), ['category_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_definitions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_definitions_is_active'), ['is_active'], unique=False)
        batch_op.create_index('ix_analytics_report_definitions_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_report_definitions_report_type_valid', ANALYTICS_REPORT_TYPE_CHECK)
        batch_op.create_check_constraint('ck_analytics_report_definitions_status_valid', ANALYTICS_DEFINITION_STATUS_CHECK)

    op.create_table(
        'analytics_report_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('report_definition_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('is_current_draft', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_current_published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('structure_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('narrative_guidance_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
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
        sa.ForeignKeyConstraint(['report_definition_id'], ['analytics_report_definitions.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_report_versions_uuid'),
        sa.UniqueConstraint('report_definition_id', 'version_number', name='uq_analytics_report_versions_def_ver_no'),
    )
    with op.batch_alter_table('analytics_report_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_report_versions_report_definition_id'), ['report_definition_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_versions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_versions_is_current_draft'), ['is_current_draft'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_versions_is_current_published'), ['is_current_published'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_versions_published_at'), ['published_at'], unique=False)
        batch_op.create_index('ix_analytics_report_versions_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_report_versions_status_valid', ANALYTICS_VERSION_STATUS_CHECK)
        batch_op.create_check_constraint('ck_analytics_report_versions_state_valid', ANALYTICS_VERSION_STATE_CHECK)
        batch_op.create_check_constraint('ck_analytics_report_versions_publish_state_valid', ANALYTICS_VERSION_PUBLISH_STATE_CHECK)
        batch_op.create_check_constraint('ck_analytics_report_versions_published_at_valid', ANALYTICS_VERSION_PUBLISHED_AT_CHECK)

    op.create_index(
        'ux_analytics_report_versions_one_cur_draft_per_def',
        'analytics_report_versions',
        ['report_definition_id'],
        unique=True,
        postgresql_where=sa.text('is_current_draft = true AND deleted_at IS NULL'),
    )
    op.create_index(
        'ux_analytics_report_versions_one_cur_pub_per_def',
        'analytics_report_versions',
        ['report_definition_id'],
        unique=True,
        postgresql_where=sa.text('is_current_published = true AND deleted_at IS NULL'),
    )

    op.create_table(
        'analytics_indicator_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('indicator_key', sa.String(length=150), nullable=False),
        sa.Column('indicator_code', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_mode', sa.String(length=50), nullable=False, server_default='dataset_driven'),
        sa.Column('calculation_type', sa.String(length=60), nullable=False, server_default='absolute_count'),
        sa.Column('target_source_type', sa.String(length=60), nullable=False, server_default='manual_central_target'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
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
        sa.UniqueConstraint('uuid', name='uq_analytics_indicator_definitions_uuid'),
        sa.UniqueConstraint('indicator_key', name='uq_analytics_indicator_definitions_indicator_key'),
    )
    with op.batch_alter_table('analytics_indicator_definitions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_indicator_definitions_indicator_code'), ['indicator_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_definitions_source_mode'), ['source_mode'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_definitions_calculation_type'), ['calculation_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_definitions_target_source_type'), ['target_source_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_definitions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_definitions_is_active'), ['is_active'], unique=False)
        batch_op.create_index('ix_analytics_indicator_definitions_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_indicator_definitions_source_mode_valid', ANALYTICS_INDICATOR_SOURCE_MODE_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_definitions_calculation_type_valid', ANALYTICS_INDICATOR_CALCULATION_TYPE_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_definitions_target_source_type_valid', ANALYTICS_INDICATOR_TARGET_SOURCE_TYPE_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_definitions_status_valid', ANALYTICS_DEFINITION_STATUS_CHECK)

    op.create_table(
        'analytics_indicator_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('indicator_definition_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('dataset_version_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('is_current_draft', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_current_published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('period_mode', sa.String(length=50), nullable=False, server_default='yearly'),
        sa.Column('aggregation_strategy', sa.String(length=50), nullable=False, server_default='sum'),
        sa.Column('unit_label', sa.String(length=100), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('formula_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('target_config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('narrative_guidance_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('threshold_rules_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_ARRAY),
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
        sa.ForeignKeyConstraint(['indicator_definition_id'], ['analytics_indicator_definitions.id']),
        sa.ForeignKeyConstraint(['dataset_id'], ['analytics_datasets.id']),
        sa.ForeignKeyConstraint(['dataset_version_id'], ['analytics_dataset_versions.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_indicator_versions_uuid'),
        sa.UniqueConstraint('indicator_definition_id', 'version_number', name='uq_analytics_indicator_versions_def_ver_no'),
    )
    with op.batch_alter_table('analytics_indicator_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_indicator_definition_id'), ['indicator_definition_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_dataset_id'), ['dataset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_dataset_version_id'), ['dataset_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_is_current_draft'), ['is_current_draft'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_is_current_published'), ['is_current_published'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_period_mode'), ['period_mode'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_aggregation_strategy'), ['aggregation_strategy'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_indicator_versions_published_at'), ['published_at'], unique=False)
        batch_op.create_index('ix_analytics_indicator_versions_deleted_at', ['deleted_at'], unique=False)
        batch_op.create_check_constraint('ck_analytics_indicator_versions_status_valid', ANALYTICS_VERSION_STATUS_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_versions_period_mode_valid', ANALYTICS_PERIOD_MODE_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_versions_aggregation_strategy_valid', ANALYTICS_AGGREGATION_STRATEGY_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_versions_state_valid', ANALYTICS_VERSION_STATE_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_versions_publish_state_valid', ANALYTICS_VERSION_PUBLISH_STATE_CHECK)
        batch_op.create_check_constraint('ck_analytics_indicator_versions_published_at_valid', ANALYTICS_VERSION_PUBLISHED_AT_CHECK)

    op.create_index(
        'ux_analytics_indicator_versions_one_cur_draft_per_def',
        'analytics_indicator_versions',
        ['indicator_definition_id'],
        unique=True,
        postgresql_where=sa.text('is_current_draft = true AND deleted_at IS NULL'),
    )
    op.create_index(
        'ux_analytics_indicator_versions_one_cur_pub_per_def',
        'analytics_indicator_versions',
        ['indicator_definition_id'],
        unique=True,
        postgresql_where=sa.text('is_current_published = true AND deleted_at IS NULL'),
    )

    op.create_table(
        'analytics_report_version_indicators',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('report_version_id', sa.Integer(), nullable=False),
        sa.Column('indicator_version_id', sa.Integer(), nullable=False),
        sa.Column('item_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('display_label', sa.String(length=255), nullable=True),
        sa.Column('section_key', sa.String(length=100), nullable=True),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSONB_EMPTY_OBJECT),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_by_uuid', sa.String(length=36), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('deleted_by_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['report_version_id'], ['analytics_report_versions.id']),
        sa.ForeignKeyConstraint(['indicator_version_id'], ['analytics_indicator_versions.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.UniqueConstraint('uuid', name='uq_analytics_report_version_indicators_uuid'),
        sa.UniqueConstraint('report_version_id', 'indicator_version_id', name='uq_analytics_report_ver_indicators_rv_iv'),
    )
    with op.batch_alter_table('analytics_report_version_indicators', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analytics_report_version_indicators_report_version_id'), ['report_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_version_indicators_indicator_version_id'), ['indicator_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analytics_report_version_indicators_section_key'), ['section_key'], unique=False)
        batch_op.create_index('ix_analytics_report_version_indicators_deleted_at', ['deleted_at'], unique=False)


def downgrade():
    op.drop_index('ux_analytics_indicator_versions_one_cur_pub_per_def', table_name='analytics_indicator_versions')
    op.drop_index('ux_analytics_indicator_versions_one_cur_draft_per_def', table_name='analytics_indicator_versions')
    op.drop_index('ux_analytics_report_versions_one_cur_pub_per_def', table_name='analytics_report_versions')
    op.drop_index('ux_analytics_report_versions_one_cur_draft_per_def', table_name='analytics_report_versions')
    op.drop_table('analytics_report_version_indicators')
    op.drop_table('analytics_indicator_versions')
    op.drop_table('analytics_indicator_definitions')
    op.drop_table('analytics_report_versions')
    op.drop_table('analytics_report_definitions')
