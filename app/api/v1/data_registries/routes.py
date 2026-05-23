from flask import Blueprint, current_app, request

from app.core.extensions import db
from app.core.utils import json_response
from app.modules.data_registry.services import (
    DataRegistryImportBatchService,
    DataRegistryImportValidationService,
    DataRegistryMaterializationService,
    DataRegistryQueryService,
    DataRegistryVersionService,
)


api_data_registry_bp = Blueprint(
    'api_data_registry_v1',
    __name__,
    url_prefix='/api/v1',
)


def validation_error_response(error):
    return json_response(
        False,
        str(error),
        data={'error_type': 'validation_error'},
        status=400,
    )


def authorization_error_response(error):
    return json_response(
        False,
        str(error),
        data={'error_type': 'authorization_error'},
        status=403,
    )


def serialize_registry(registry):
    if not registry:
        return None
    if isinstance(registry, dict):
        return registry
    return {
        'id': registry.id,
        'uuid': registry.uuid,
        'registry_slug': registry.registry_slug,
        'registry_code': registry.registry_code,
        'name': registry.name,
        'description': registry.description,
        'registry_type': registry.registry_type,
        'category_key': registry.category_key,
        'source_mode': registry.source_mode,
        'data_shape': registry.data_shape,
        'is_year_scoped': registry.is_year_scoped,
        'status': registry.status,
        'schema_meta': registry.schema_meta,
        'created_at': registry.created_at.isoformat() if getattr(registry, 'created_at', None) else None,
        'updated_at': registry.updated_at.isoformat() if getattr(registry, 'updated_at', None) else None,
    }


def serialize_version(version):
    if not version:
        return None
    if isinstance(version, dict):
        return version
    return {
        'id': version.id,
        'uuid': version.uuid,
        'registry_id': version.registry_id,
        'version_number': version.version_number,
        'status': version.status,
        'schema_json': version.schema_json,
        'mapping_spec': version.mapping_spec,
        'source_snapshot': version.source_snapshot,
        'publish_notes': version.publish_notes,
        'published_at': version.published_at.isoformat() if getattr(version, 'published_at', None) else None,
        'materialized_at': version.materialized_at.isoformat() if getattr(version, 'materialized_at', None) else None,
        'materialization_metadata': getattr(version, 'materialization_metadata', None) or {},
        'source_watermark': version.source_watermark,
        'materialized_watermark': version.materialized_watermark,
        'freshness_status': version.freshness_status,
        'freshness_signature': version.freshness_signature,
        'created_at': version.created_at.isoformat() if getattr(version, 'created_at', None) else None,
        'updated_at': version.updated_at.isoformat() if getattr(version, 'updated_at', None) else None,
    }


def serialize_import_batch(batch):
    if not batch:
        return None
    if isinstance(batch, dict):
        return batch
    return {
        'id': batch.id,
        'uuid': batch.uuid,
        'registry_id': batch.registry_id,
        'registry_version_id': batch.registry_version_id,
        'batch_type': batch.batch_type,
        'status': batch.status,
        'original_filename': batch.original_filename,
        'mime_type': batch.mime_type,
        'reporting_year': batch.reporting_year,
        'total_rows': batch.total_rows,
        'mapped_rows': batch.mapped_rows,
        'valid_rows': batch.valid_rows,
        'error_rows': batch.error_rows,
        'duplicate_rows': batch.duplicate_rows,
        'skipped_rows': batch.skipped_rows,
        'mapping_snapshot': batch.mapping_snapshot,
        'source_headers': batch.source_headers,
        'source_snapshot': batch.source_snapshot,
        'validation_summary': batch.validation_summary,
        'materialized_at': batch.materialized_at.isoformat() if getattr(batch, 'materialized_at', None) else None,
        'materialized_by': batch.materialized_by,
        'materialized_by_uuid': batch.materialized_by_uuid,
        'materialization_summary': batch.materialization_summary,
        'created_at': batch.created_at.isoformat() if getattr(batch, 'created_at', None) else None,
        'updated_at': batch.updated_at.isoformat() if getattr(batch, 'updated_at', None) else None,
    }


def serialize_import_row(row):
    if not row:
        return None
    if isinstance(row, dict):
        return row
    return {
        'id': row.id,
        'uuid': row.uuid,
        'import_batch_id': row.import_batch_id,
        'row_number': row.row_number,
        'row_hash': row.row_hash,
        'status': row.status,
        'record_key_candidate': row.record_key_candidate,
        'record_code_candidate': row.record_code_candidate,
        'duplicate_of_row_id': row.duplicate_of_row_id,
        'raw_payload': row.raw_payload,
        'mapped_payload': row.mapped_payload,
        'normalized_payload': row.normalized_payload,
        'validation_errors': row.validation_errors,
        'validation_warnings': row.validation_warnings,
        'lineage_snapshot': row.lineage_snapshot,
        'created_at': row.created_at.isoformat() if getattr(row, 'created_at', None) else None,
        'updated_at': row.updated_at.isoformat() if getattr(row, 'updated_at', None) else None,
    }


@api_data_registry_bp.route('/data-registry-versions/<int:version_id>', methods=['GET'])
def get_registry_version_detail(version_id):
    try:
        result = DataRegistryVersionService().get_version_detail(version_id)
        return json_response(
            True,
            'Detail version registry berhasil diambil.',
            {
                'version': serialize_version(result.get('version')),
                'batches': [serialize_import_batch(batch) for batch in result.get('batches', [])],
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Get registry version detail API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get registry version detail API error: {str(error)}')
        return json_response(False, 'Gagal mengambil detail version registry.', status=500)


@api_data_registry_bp.route('/data-registry-versions/<int:version_id>/import-batches', methods=['POST'])
def create_import_batch(version_id):
    try:
        payload = request.get_json(silent=True) or {}
        result = DataRegistryImportBatchService().create_batch(version_id, payload, actor=None)
        return json_response(
            True,
            'Import batch berhasil dibuat.',
            {
                'batch': serialize_import_batch(result.get('batch')),
                'rows': [serialize_import_row(row) for row in result.get('rows', [])],
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Create import batch API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Create import batch API error: {str(error)}')
        return json_response(False, 'Gagal membuat import batch.', status=500)


@api_data_registry_bp.route('/data-registry-import-batches/<int:batch_id>', methods=['GET'])
def get_import_batch_detail(batch_id):
    try:
        result = DataRegistryImportBatchService().get_batch_detail(batch_id)
        return json_response(
            True,
            'Detail import batch berhasil diambil.',
            {
                'batch': serialize_import_batch(result.get('batch')),
                'version': serialize_version(result.get('version')),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Get import batch detail API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get import batch detail API error: {str(error)}')
        return json_response(False, 'Gagal mengambil detail import batch.', status=500)


@api_data_registry_bp.route('/data-registry-import-batches/<int:batch_id>/validate', methods=['POST'])
def validate_import_batch(batch_id):
    try:
        result = DataRegistryImportValidationService().validate_batch(batch_id, actor=None)
        return json_response(
            True,
            'Import batch berhasil divalidasi.',
            {'batch': serialize_import_batch(result.get('batch'))},
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Validate import batch API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Validate import batch API error: {str(error)}')
        return json_response(False, 'Gagal memvalidasi import batch.', status=500)


@api_data_registry_bp.route('/data-registry-import-batches/<int:batch_id>/rows', methods=['GET'])
def list_import_batch_rows(batch_id):
    try:
        result = DataRegistryImportBatchService().list_batch_rows(
            batch_id,
            status=request.args.get('status'),
        )
        return json_response(
            True,
            'Row import batch berhasil diambil.',
            {
                'batch': serialize_import_batch(result.get('batch')),
                'rows': [serialize_import_row(row) for row in result.get('rows', [])],
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'List import batch rows API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'List import batch rows API error: {str(error)}')
        return json_response(False, 'Gagal mengambil row import batch.', status=500)


@api_data_registry_bp.route('/data-registry-import-batches/<int:batch_id>/materialize', methods=['POST'])
def materialize_import_batch(batch_id):
    try:
        result = DataRegistryMaterializationService().materialize_import_batch(batch_id, actor=None)
        return json_response(
            True,
            'Import batch berhasil dimaterialisasi.',
            {
                'batch': serialize_import_batch(result.get('batch')),
                'registry': serialize_registry(result.get('registry')),
                'version': serialize_version(result.get('version')),
                'materialization': result.get('materialization', {}),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Materialize import batch API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Materialize import batch API error: {str(error)}')
        return json_response(False, 'Gagal mematerialisasi import batch.', status=500)


@api_data_registry_bp.route('/registry-resources/<string:registry_slug>/options', methods=['GET'])
def get_registry_options(registry_slug):
    try:
        result = DataRegistryQueryService().get_option_list(
            registry_slug,
            version_number=request.args.get('version_number', type=int),
            admin_level=request.args.get('admin_level'),
            parent_record_id=request.args.get('parent_record_id', type=int),
            parent_code=request.args.get('parent_code'),
            q=request.args.get('q'),
            limit=request.args.get('limit', default=100, type=int),
        )
        return json_response(
            True,
            'Option registry berhasil diambil.',
            {
                'registry': serialize_registry(result.get('registry')),
                'version': serialize_version(result.get('version')),
                'items': result.get('items', []),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Get registry options API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get registry options API error: {str(error)}')
        return json_response(False, 'Gagal mengambil option registry.', status=500)


@api_data_registry_bp.route('/registry-resources/<string:registry_slug>/lookup', methods=['GET'])
def get_registry_lookup(registry_slug):
    try:
        result = DataRegistryQueryService().get_lookup(
            registry_slug,
            record_key=request.args.get('record_key'),
            record_code=request.args.get('record_code'),
            version_number=request.args.get('version_number', type=int),
        )
        return json_response(
            True,
            'Lookup registry berhasil diambil.',
            {
                'registry': serialize_registry(result.get('registry')),
                'version': serialize_version(result.get('version')),
                'record': result.get('record'),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Get registry lookup API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get registry lookup API error: {str(error)}')
        return json_response(False, 'Gagal mengambil lookup registry.', status=500)


@api_data_registry_bp.route('/registry-resources/<string:registry_slug>/children', methods=['GET'])
def get_registry_children(registry_slug):
    try:
        result = DataRegistryQueryService().get_children(
            registry_slug,
            parent_record_id=request.args.get('parent_record_id', type=int),
            parent_code=request.args.get('parent_code'),
            admin_level=request.args.get('admin_level'),
            version_number=request.args.get('version_number', type=int),
        )
        return json_response(
            True,
            'Children registry berhasil diambil.',
            {
                'registry': serialize_registry(result.get('registry')),
                'version': serialize_version(result.get('version')),
                'items': result.get('items', []),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Get registry children API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get registry children API error: {str(error)}')
        return json_response(False, 'Gagal mengambil children registry.', status=500)


@api_data_registry_bp.route('/registry-resources/<string:registry_slug>/tree', methods=['GET'])
def get_registry_tree(registry_slug):
    try:
        result = DataRegistryQueryService().get_tree(
            registry_slug,
            root_level=request.args.get('root_level', default='province'),
            max_depth=request.args.get('max_depth', default=4, type=int),
            version_number=request.args.get('version_number', type=int),
        )
        return json_response(
            True,
            'Tree registry berhasil diambil.',
            {
                'registry': serialize_registry(result.get('registry')),
                'version': serialize_version(result.get('version')),
                'items': result.get('items', []),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Get registry tree API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get registry tree API error: {str(error)}')
        return json_response(False, 'Gagal mengambil tree registry.', status=500)


@api_data_registry_bp.route('/registry-resources/<string:registry_slug>/feature-collection', methods=['GET'])
def get_registry_feature_collection(registry_slug):
    try:
        feature_collection = DataRegistryQueryService().get_feature_collection(
            registry_slug,
            admin_level=request.args.get('admin_level'),
            parent_code=request.args.get('parent_code'),
            version_number=request.args.get('version_number', type=int),
        )
        return json_response(
            True,
            'Feature collection registry berhasil diambil.',
            {
                'feature_collection': feature_collection,
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(
            f'Get registry feature collection API authorization error: {str(error)}'
        )
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Get registry feature collection API error: {str(error)}')
        return json_response(False, 'Gagal mengambil feature collection registry.', status=500)
