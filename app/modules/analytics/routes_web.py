import json

from flask import Blueprint, current_app, render_template, url_for

from app.modules.analytics.services import AnalyticsQueryService
from app.modules.data_registry.services import DataRegistryService, DataRegistryVersionService


analytics_web_bp = Blueprint('analytics_web', __name__)


PREVIEW_ROW_LIMIT = 8


def _normalize_text(value):
    return str(value or '').strip().lower()


def _serialize_registry_summary(registry, published_version=None):
    return {
        'id': getattr(registry, 'id', None),
        'name': getattr(registry, 'name', None),
        'description': getattr(registry, 'description', None),
        'registry_slug': getattr(registry, 'registry_slug', None),
        'registry_code': getattr(registry, 'registry_code', None),
        'registry_type': getattr(registry, 'registry_type', None),
        'category_key': getattr(registry, 'category_key', None),
        'source_mode': getattr(registry, 'source_mode', None),
        'data_shape': getattr(registry, 'data_shape', None),
        'status': getattr(registry, 'status', None),
        'published_version_number': getattr(published_version, 'version_number', None),
    }


def _build_registry_browser_items(registries, version_service):
    items = []
    for registry in registries:
        draft_version = version_service.repository.get_draft_version(registry.id)
        published_version = version_service.repository.get_published_version(registry.id)
        items.append({
            'registry': registry,
            'draft_version': draft_version,
            'published_version': published_version,
        })
    return items


def _collect_structured_registry_refs(payload, refs=None):
    refs = refs or set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {
                'registry_id',
                'registry_uuid',
                'registry_code',
                'registry_slug',
                'registry_name',
                'data_registry_id',
                'data_registry_uuid',
                'data_registry_code',
                'data_registry_slug',
                'data_registry_name',
                'analytics_registry_id',
                'analytics_registry_uuid',
                'analytics_registry_code',
                'analytics_registry_slug',
                'primary_registry_id',
                'primary_registry_uuid',
                'primary_registry_code',
                'primary_registry_slug',
                'join_registry_id',
                'join_registry_uuid',
                'join_registry_code',
                'join_registry_slug',
            }:
                refs.add(_normalize_text(value))
            _collect_structured_registry_refs(value, refs=refs)
    elif isinstance(payload, list):
        for item in payload:
            _collect_structured_registry_refs(item, refs=refs)
    return refs


def _dataset_matches_registry(dataset_item, registry):
    dataset = dataset_item.get('dataset')
    active_version = dataset_item.get('published_version') or dataset_item.get('draft_version')

    registry_refs = {
        _normalize_text(getattr(registry, 'id', None)),
        _normalize_text(getattr(registry, 'uuid', None)),
        _normalize_text(getattr(registry, 'registry_slug', None)),
        _normalize_text(getattr(registry, 'registry_code', None)),
    }
    registry_refs = {value for value in registry_refs if value}
    if not registry_refs:
        return False

    primary_source_ref = _normalize_text(getattr(dataset, 'primary_source_ref', None))
    if primary_source_ref and primary_source_ref in registry_refs:
        return True

    structured_refs = set()
    for payload in (
        getattr(dataset, 'settings_json', {}) or {},
        getattr(active_version, 'source_contract_json', {}) or {},
        getattr(active_version, 'join_registry_spec_json', {}) or {},
    ):
        structured_refs.update(_collect_structured_registry_refs(payload))

    return any(ref in registry_refs for ref in structured_refs if ref)


def _build_related_dataset_items(registry, dataset_items):
    return [item for item in dataset_items if _dataset_matches_registry(item, registry)]


@analytics_web_bp.route('/analytics', methods=['GET'])
def analytics_workspace():
    """Menampilkan daftar registry publish sebagai pintu masuk analytics Domain 5."""

    error_message = None
    registry_items = []
    published_registry_items = []
    analytics_dataset_items = []

    try:
        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registries = registry_service.repository.get_all()
        registry_items = _build_registry_browser_items(registries, version_service)
        analytics_dataset_items = AnalyticsQueryService().list_datasets()

        for item in registry_items:
            published_version = item.get('published_version')
            if not published_version:
                continue
            related_datasets = _build_related_dataset_items(item['registry'], analytics_dataset_items)
            published_registry_items.append({
                **item,
                'related_dataset_count': len(related_datasets),
            })
    except Exception as error:
        current_app.logger.error('Analytics registry index error: %s', str(error))
        error_message = 'Gagal memuat daftar analytics registry.'

    return render_template(
        'pages/analytics/index.html',
        registry_items=published_registry_items,
        total_published_registries=len(published_registry_items),
        total_related_datasets=sum(item.get('related_dataset_count', 0) for item in published_registry_items),
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/reports/<int:registry_id>', methods=['GET'])
def analytics_report_detail(registry_id):
    """Menampilkan detail report analytics yang fokus pada filter, KPI, chart, dan peta."""

    error_message = None
    workspace = None
    analytics_dataset_items = []
    related_dataset_items = []

    try:
        workspace = DataRegistryService().get_registry_workspace(registry_id, record_limit=PREVIEW_ROW_LIMIT)
        registry = (workspace or {}).get('registry')
        if not registry:
            raise ValueError('Data registry tidak ditemukan.')

        analytics_dataset_items = AnalyticsQueryService().list_datasets()
        related_dataset_items = _build_related_dataset_items(registry, analytics_dataset_items)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics report detail error: %s', str(error))
        error_message = 'Gagal memuat detail report analytics.'

    registry = (workspace or {}).get('registry')
    published_version = (workspace or {}).get('published_version')
    primary_dataset = related_dataset_items[0] if related_dataset_items else None
    workspace_config = {
        'analyticsDatasetsUrl': url_for('api_analytics_v1.list_dataset_definitions'),
        'analyticsDatasetDetailUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__',
        'analyticsDatasetRunsUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__/runs',
        'analyticsDatasetExecuteUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__/versions/__DATASET_VERSION_ID__/runs',
        'initialRegistry': _serialize_registry_summary(registry, published_version),
        'initialDatasetId': getattr(primary_dataset.get('dataset'), 'id', None) if primary_dataset else None,
        'allowedDatasetIds': [getattr(item.get('dataset'), 'id', None) for item in related_dataset_items if getattr(item.get('dataset'), 'id', None) is not None],
    }

    return render_template(
        'pages/analytics/detail_report.html',
        registry=registry,
        published_version=published_version,
        related_dataset_items=related_dataset_items,
        related_dataset_count=len(related_dataset_items),
        primary_dataset=primary_dataset.get('dataset') if primary_dataset else None,
        workspace_config=workspace_config,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/reports/<int:registry_id>/metadata', methods=['GET'])
def analytics_report_metadata(registry_id):
    """Menampilkan metadata registry terpisah dari panel insight agar interaksi chart lebih fokus."""

    error_message = None
    workspace = None
    related_dataset_items = []

    try:
        workspace = DataRegistryService().get_registry_workspace(registry_id, record_limit=PREVIEW_ROW_LIMIT)
        registry = (workspace or {}).get('registry')
        if not registry:
            raise ValueError('Data registry tidak ditemukan.')
        related_dataset_items = _build_related_dataset_items(registry, AnalyticsQueryService().list_datasets())
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics metadata detail error: %s', str(error))
        error_message = 'Gagal memuat metadata analytics registry.'

    return render_template(
        'pages/analytics/detail_metadata.html',
        registry=(workspace or {}).get('registry'),
        draft_version=(workspace or {}).get('draft_version'),
        published_version=(workspace or {}).get('published_version'),
        manual_entry_version=(workspace or {}).get('manual_entry_version'),
        record_count=(workspace or {}).get('record_count') or 0,
        related_dataset_items=related_dataset_items,
        error_message=error_message,
    )
