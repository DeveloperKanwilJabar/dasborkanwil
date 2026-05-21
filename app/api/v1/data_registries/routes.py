from flask import Blueprint, current_app, request

from app.core.extensions import db
from app.core.utils import json_response
from app.modules.data_registry.services import DataRegistryQueryService


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
        'source_watermark': version.source_watermark,
        'materialized_watermark': version.materialized_watermark,
        'freshness_status': version.freshness_status,
        'freshness_signature': version.freshness_signature,
        'created_at': version.created_at.isoformat() if getattr(version, 'created_at', None) else None,
        'updated_at': version.updated_at.isoformat() if getattr(version, 'updated_at', None) else None,
    }


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
