"""backfill data registry materialization metadata

Revision ID: c4d7a9e2b1f0
Revises: 9f2d6c4b1a7e
Create Date: 2026-05-26 09:25:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c4d7a9e2b1f0'
down_revision = '9f2d6c4b1a7e'
branch_labels = None
depends_on = None


LEGACY_REGISTRY_TYPE_CHECK = "registry_type IN ('geo')"
LEGACY_REGISTRY_DATA_SHAPE_CHECK = "data_shape IN ('hierarchical_geo', 'geojson')"
UPDATED_REGISTRY_TYPE_CHECK = "registry_type IN ('geo', 'master_data')"
UPDATED_REGISTRY_DATA_SHAPE_CHECK = "data_shape IN ('hierarchical_geo', 'geojson', 'hierarchical', 'tabular')"
LEGACY_IMPORT_BATCH_TYPE_CHECK = "batch_type IN ('file_upload', 'manual_seed', 'sync_snapshot')"
UPDATED_IMPORT_BATCH_TYPE_CHECK = "batch_type IN ('file_upload', 'manual_seed', 'manual_entry', 'sync_snapshot')"
LEGACY_RECORD_ADMIN_LEVEL_CHECK = "admin_level IN ('province', 'city_regency', 'district', 'village')"
UPDATED_RECORD_ADMIN_LEVEL_CHECK = (
    "admin_level IN ('province', 'city_regency', 'district', 'village', 'master_data')"
)


batch_table = sa.table(
    'data_registry_import_batches',
    sa.column('id', sa.Integer()),
    sa.column('status', sa.String()),
    sa.column('materialized_at', sa.DateTime(timezone=True)),
    sa.column('validation_summary', postgresql.JSONB(astext_type=sa.Text())),
    sa.column('materialization_summary', postgresql.JSONB(astext_type=sa.Text())),
)

version_table = sa.table(
    'data_registry_versions',
    sa.column('id', sa.Integer()),
    sa.column('materialized_at', sa.DateTime(timezone=True)),
    sa.column('materialization_metadata', postgresql.JSONB(astext_type=sa.Text())),
    sa.column('materialized_watermark', sa.String()),
    sa.column('freshness_signature', sa.String()),
    sa.column('freshness_status', sa.String()),
)


def _first_non_empty(*values):
    for value in values:
        if value not in (None, '', {}):
            return value
    return None


def _resolve_materialization_contract(projection):
    return (
        projection.get('batch_contract')
        or projection.get('version_contract')
        or 'generic_v1'
    )


def build_legacy_materialization_summary(projection):
    return {
        'record_count': int(projection.get('record_count') or 0),
        'source_row_count': int(projection.get('source_row_count') or 0),
        'materialization_contract': _resolve_materialization_contract(projection),
    }


def build_legacy_version_materialization_metadata(projection):
    summary = build_legacy_materialization_summary(projection)
    return {
        'materialization_contract': summary['materialization_contract'],
        'source_row_count': summary['source_row_count'],
        'record_count': summary['record_count'],
        'batch_id': projection.get('batch_id'),
        'batch_uuid': projection.get('batch_uuid'),
        'source_name': projection.get('source_name'),
    }


def build_legacy_batch_backfill_patch(projection):
    summary = build_legacy_materialization_summary(projection)
    validation_summary = dict(projection.get('existing_validation_summary') or {})
    validation_summary['materialization'] = summary
    materialized_at = _first_non_empty(
        projection.get('existing_batch_materialized_at'),
        projection.get('batch_materialized_at'),
        projection.get('batch_updated_at'),
        projection.get('batch_created_at'),
        projection.get('version_updated_at'),
        projection.get('version_created_at'),
    )

    return {
        'status': 'materialized',
        'materialized_at': materialized_at,
        'validation_summary': validation_summary,
        'materialization_summary': summary,
    }


def build_legacy_version_backfill_patch(projection):
    materialized_at = _first_non_empty(
        projection.get('existing_version_materialized_at'),
        projection.get('batch_materialized_at'),
        projection.get('batch_updated_at'),
        projection.get('batch_created_at'),
        projection.get('version_updated_at'),
        projection.get('version_created_at'),
    )
    summary = build_legacy_materialization_summary(projection)
    metadata = build_legacy_version_materialization_metadata(projection)
    batch_id = projection.get('batch_id')
    version_id = projection.get('version_id')

    return {
        'materialized_at': materialized_at,
        'materialization_metadata': metadata,
        'materialized_watermark': projection.get('existing_materialized_watermark') or (
            f"legacy-backfill:batch:{batch_id}:records:{summary['record_count']}:rows:{summary['source_row_count']}"
        ),
        'freshness_signature': projection.get('existing_freshness_signature') or (
            f"legacy-backfill:version:{version_id}:batch:{batch_id}:records:{summary['record_count']}:rows:{summary['source_row_count']}"
        ),
        'freshness_status': projection.get('existing_freshness_status') or 'fresh',
    }


def upgrade():
    with op.batch_alter_table('data_registries', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registries_registry_type_valid', type_='check')
        batch_op.drop_constraint('ck_data_registries_data_shape_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registries_registry_type_valid',
            UPDATED_REGISTRY_TYPE_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_data_registries_data_shape_valid',
            UPDATED_REGISTRY_DATA_SHAPE_CHECK,
        )

    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_batch_type_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_import_batches_batch_type_valid',
            UPDATED_IMPORT_BATCH_TYPE_CHECK,
        )

    with op.batch_alter_table('data_registry_records', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_records_admin_level_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_records_admin_level_valid',
            UPDATED_RECORD_ADMIN_LEVEL_CHECK,
        )

    bind = op.get_bind()
    projections = bind.execute(
        sa.text(
            """
            WITH record_counts AS (
                SELECT
                    registry_version_id,
                    COUNT(*)::int AS record_count
                FROM data_registry_records
                WHERE deleted_at IS NULL
                GROUP BY registry_version_id
            ),
            latest_batches AS (
                SELECT DISTINCT ON (b.registry_version_id)
                    b.id AS batch_id,
                    b.uuid AS batch_uuid,
                    b.registry_version_id AS version_id,
                    COALESCE(b.valid_rows, 0)::int AS source_row_count,
                    b.status AS existing_batch_status,
                    b.materialized_at AS existing_batch_materialized_at,
                    b.materialized_at AS batch_materialized_at,
                    b.updated_at AS batch_updated_at,
                    b.created_at AS batch_created_at,
                    b.validation_summary AS existing_validation_summary,
                    b.materialization_summary AS existing_materialization_summary,
                    b.mapping_snapshot ->> 'materialization_contract' AS batch_contract,
                    b.source_snapshot ->> 'source_name' AS source_name,
                    v.mapping_spec ->> 'materialization_contract' AS version_contract,
                    v.materialized_at AS existing_version_materialized_at,
                    v.materialization_metadata AS existing_version_materialization_metadata,
                    v.materialized_watermark AS existing_materialized_watermark,
                    v.freshness_signature AS existing_freshness_signature,
                    v.freshness_status AS existing_freshness_status,
                    v.updated_at AS version_updated_at,
                    v.created_at AS version_created_at,
                    rc.record_count
                FROM data_registry_import_batches b
                JOIN data_registry_versions v ON v.id = b.registry_version_id
                JOIN record_counts rc ON rc.registry_version_id = v.id
                WHERE b.deleted_at IS NULL
                  AND v.deleted_at IS NULL
                  AND rc.record_count > 0
                  AND b.status IN ('validated', 'materialized')
                ORDER BY
                    b.registry_version_id,
                    COALESCE(b.materialized_at, b.updated_at, b.created_at) DESC,
                    b.id DESC
            )
            SELECT *
            FROM latest_batches
            WHERE
                existing_batch_materialized_at IS NULL
                OR existing_batch_status = 'validated'
                OR COALESCE(existing_materialization_summary, '{}'::jsonb) = '{}'::jsonb
                OR COALESCE(existing_validation_summary -> 'materialization', 'null'::jsonb) = 'null'::jsonb
                OR existing_version_materialized_at IS NULL
                OR COALESCE(existing_version_materialization_metadata, '{}'::jsonb) = '{}'::jsonb
                OR existing_materialized_watermark IS NULL
                OR existing_freshness_signature IS NULL
                OR COALESCE(existing_freshness_status, 'unknown') = 'unknown'
            """
        )
    ).mappings().all()

    for projection in projections:
        batch_patch = build_legacy_batch_backfill_patch(projection)
        bind.execute(
            batch_table.update()
            .where(batch_table.c.id == projection['batch_id'])
            .values(**batch_patch)
        )

        version_patch = build_legacy_version_backfill_patch(projection)
        bind.execute(
            version_table.update()
            .where(version_table.c.id == projection['version_id'])
            .values(**version_patch)
        )


def downgrade():
    with op.batch_alter_table('data_registry_records', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_records_admin_level_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_records_admin_level_valid',
            LEGACY_RECORD_ADMIN_LEVEL_CHECK,
        )

    with op.batch_alter_table('data_registry_import_batches', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registry_import_batches_batch_type_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registry_import_batches_batch_type_valid',
            LEGACY_IMPORT_BATCH_TYPE_CHECK,
        )

    with op.batch_alter_table('data_registries', schema=None) as batch_op:
        batch_op.drop_constraint('ck_data_registries_registry_type_valid', type_='check')
        batch_op.drop_constraint('ck_data_registries_data_shape_valid', type_='check')
        batch_op.create_check_constraint(
            'ck_data_registries_registry_type_valid',
            LEGACY_REGISTRY_TYPE_CHECK,
        )
        batch_op.create_check_constraint(
            'ck_data_registries_data_shape_valid',
            LEGACY_REGISTRY_DATA_SHAPE_CHECK,
        )
