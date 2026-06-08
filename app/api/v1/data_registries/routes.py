from flask import Blueprint, current_app, request
from flasgger import swag_from

from app.api.docs import (
    build_spec,
    envelope_schema,
    path_parameter,
    query_parameter,
    standard_responses,
)
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

REGISTRY_VERSION_DETAIL_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil detail version registry.',
    description='Mengembalikan detail version registry beserta ringkasan import batch yang terkait.',
    parameters=[path_parameter('version_id', description='ID version registry.', example=31)],
    responses=standard_responses(envelope_schema({'type': 'object'} , message_example='Detail version registry berhasil diambil.'), 'Detail version registry berhasil diambil.'),
)

CREATE_IMPORT_BATCH_DOC = build_spec(
    tag='Data Registry',
    summary='Buat import batch registry.',
    description='Membuat batch import baru dari payload mapping/rows hasil upload atau manual entry.',
    parameters=[path_parameter('version_id', description='ID version registry.', example=31)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Import batch berhasil dibuat.'), 'Import batch berhasil dibuat.'),
)

IMPORT_BATCH_DETAIL_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil detail import batch.',
    description='Dipakai untuk menampilkan status batch, versi registry, dan metadata materialisasi.',
    parameters=[path_parameter('batch_id', description='ID import batch.', example=101)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Detail import batch berhasil diambil.'), 'Detail import batch berhasil diambil.'),
)

VALIDATE_IMPORT_BATCH_DOC = build_spec(
    tag='Data Registry',
    summary='Validasi import batch.',
    description='Menjalankan validasi schema, normalisasi, duplicate detection, dan merangkum hasil validasi batch.',
    parameters=[path_parameter('batch_id', description='ID import batch yang divalidasi.', example=101)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Import batch berhasil divalidasi.'), 'Import batch berhasil divalidasi.'),
)

LIST_IMPORT_BATCH_ROWS_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil daftar row pada import batch.',
    description='Mengembalikan seluruh row import batch, opsional difilter dengan status row.',
    parameters=[
        path_parameter('batch_id', description='ID import batch.', example=101),
        query_parameter('status', description='Filter status row, mis. valid/error/duplicate.', example='error'),
    ],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Row import batch berhasil diambil.'), 'Row import batch berhasil diambil.'),
)

MATERIALIZE_IMPORT_BATCH_DOC = build_spec(
    tag='Data Registry',
    summary='Materialisasi import batch ke registry records.',
    description='Menulis row valid dari import batch menjadi record registry final sesuai contract materialization yang aktif.',
    parameters=[path_parameter('batch_id', description='ID import batch.', example=101)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Import batch berhasil dimaterialisasi.'), 'Import batch berhasil dimaterialisasi.'),
)

REGISTRY_OPTIONS_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil option list registry resource.',
    description='Umumnya dipakai Select2/cascade selector untuk dropdown registry seperti wilayah.',
    parameters=[
        path_parameter('registry_slug', value_type='string', description='Slug registry resource.', example='wilayah.administratif'),
        query_parameter('version_number', value_type='integer', description='Versi registry yang ingin dipakai.', example=3),
        query_parameter('admin_level', description='Filter level administrasi.', example='city_regency'),
        query_parameter('parent_record_id', value_type='integer', description='Filter turunan berdasarkan parent ID.', example=1),
        query_parameter('parent_code', description='Filter turunan berdasarkan kode parent.', example='32'),
        query_parameter('q', description='Keyword pencarian label/kode.', example='Bandung'),
        query_parameter('limit', value_type='integer', description='Batas jumlah item.', example=100, default=100),
    ],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Option registry berhasil diambil.'), 'Option registry berhasil diambil.'),
)

REGISTRY_LOOKUP_DOC = build_spec(
    tag='Data Registry',
    summary='Lookup satu record registry.',
    description='Mengambil 1 record registry berdasarkan record_key atau record_code.',
    parameters=[
        path_parameter('registry_slug', value_type='string', description='Slug registry resource.', example='wilayah.administratif'),
        query_parameter('record_key', description='Kunci record lengkap.', example='city:3204'),
        query_parameter('record_code', description='Kode record.', example='3204'),
        query_parameter('version_number', value_type='integer', description='Versi registry.', example=3),
    ],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Lookup registry berhasil diambil.'), 'Lookup registry berhasil diambil.'),
)

REGISTRY_CHILDREN_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil child records dari satu parent registry.',
    description='Dipakai untuk tree/cascade lookup seperti parent provinsi -> daftar kabupaten/kota.',
    parameters=[
        path_parameter('registry_slug', value_type='string', description='Slug registry resource.', example='wilayah.administratif'),
        query_parameter('parent_record_id', value_type='integer', description='ID parent record.', example=1),
        query_parameter('parent_code', description='Kode parent record.', example='32'),
        query_parameter('admin_level', description='Filter level child.', example='city_regency'),
        query_parameter('version_number', value_type='integer', description='Versi registry.', example=3),
    ],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Children registry berhasil diambil.'), 'Children registry berhasil diambil.'),
)

REGISTRY_TREE_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil pohon registry bertingkat.',
    description='Mengembalikan node tree lengkap untuk kebutuhan browser hierarki wilayah/registry.',
    parameters=[
        path_parameter('registry_slug', value_type='string', description='Slug registry resource.', example='wilayah.administratif'),
        query_parameter('root_level', description='Level root awal tree.', example='province'),
        query_parameter('max_depth', value_type='integer', description='Kedalaman maksimum tree.', example=4, default=4),
        query_parameter('version_number', value_type='integer', description='Versi registry.', example=3),
    ],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Tree registry berhasil diambil.'), 'Tree registry berhasil diambil.'),
)

REGISTRY_FEATURE_COLLECTION_DOC = build_spec(
    tag='Data Registry',
    summary='Ambil GeoJSON feature collection registry.',
    description='Menghasilkan GeoJSON FeatureCollection untuk kebutuhan peta/visualisasi geospasial.',
    parameters=[
        path_parameter('registry_slug', value_type='string', description='Slug registry resource.', example='wilayah.administratif'),
        query_parameter('admin_level', description='Filter level administrasi.', example='province'),
        query_parameter('parent_code', description='Filter parent code.', example='32'),
        query_parameter('version_number', value_type='integer', description='Versi registry.', example=3),
    ],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Feature collection registry berhasil diambil.'), 'Feature collection registry berhasil diambil.'),
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
@swag_from(REGISTRY_VERSION_DETAIL_DOC)
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
@swag_from(CREATE_IMPORT_BATCH_DOC)
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
@swag_from(IMPORT_BATCH_DETAIL_DOC)
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
@swag_from(VALIDATE_IMPORT_BATCH_DOC)
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
@swag_from(LIST_IMPORT_BATCH_ROWS_DOC)
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
@swag_from(MATERIALIZE_IMPORT_BATCH_DOC)
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
@swag_from(REGISTRY_OPTIONS_DOC)
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
@swag_from(REGISTRY_LOOKUP_DOC)
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
@swag_from(REGISTRY_CHILDREN_DOC)
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
@swag_from(REGISTRY_TREE_DOC)
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
@swag_from(REGISTRY_FEATURE_COLLECTION_DOC)
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
