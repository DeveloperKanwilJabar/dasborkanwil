import json

from flask import Blueprint, current_app, render_template, request, url_for

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
        items.append(
            {
                'registry': registry,
                'draft_version': draft_version,
                'published_version': published_version,
            }
        )
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


def _find_registry_by_id(registry_items, registry_id):
    for item in registry_items:
        registry = item.get('registry')
        if getattr(registry, 'id', None) == registry_id:
            return item
    return None


def _build_linked_registry_items(dataset_item, registry_items):
    linked_items = []
    for registry_item in registry_items:
        registry = registry_item.get('registry')
        if registry and _dataset_matches_registry(dataset_item, registry):
            linked_items.append(registry_item)
    return linked_items


def _build_dataset_catalog_items(dataset_items, registry_items, report_items=None):
    report_items = report_items or []
    report_by_dataset_id = {
        getattr(item.get('report'), 'dataset_id', None): item
        for item in report_items
        if item.get('report') and getattr(item.get('report'), 'dataset_id', None) is not None
    }

    catalog_items = []
    for item in dataset_items:
        linked_registries = _build_linked_registry_items(item, registry_items)
        dataset = item.get('dataset')
        linked_report_item = report_by_dataset_id.get(getattr(dataset, 'id', None))
        catalog_items.append(
            {
                **item,
                'linked_registries': linked_registries,
                'linked_registry_count': len(linked_registries),
                'linked_report_item': linked_report_item,
            }
        )
    return catalog_items


def _build_report_builder_options():
    return {
        'report_type_options': [
            ('custom_report', 'Custom Report'),
            ('performance_report', 'Performance Report'),
            ('narrative_report', 'Narrative Report'),
            ('geo_report', 'Geo Report'),
        ],
        'period_mode_options': [
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('semester', 'Semester'),
            ('yearly', 'Yearly'),
        ],
        'quick_preset_options': [
            ('current_quarter', 'Triwulan ini'),
            ('current_semester', 'Semester ini'),
            ('current_year', 'Tahun ini'),
            ('last_7_days', '7 hari terakhir'),
            ('last_30_days', '30 hari terakhir'),
            ('last_90_days', '90 hari terakhir'),
        ],
        'block_type_options': [
            ('metric_cards', 'Metric Cards'),
            ('plotly_timeseries', 'Plotly Timeseries'),
            ('detail_table', 'Detail Table'),
            ('geo_map', 'Geo Map'),
            ('narrative', 'Narrative'),
        ],
    }


def _build_dataset_builder_options():
    return {
        'source_domain_options': [
            ('data_registry', 'Data Registry'),
            ('submission', 'Form Submission'),
            ('hybrid', 'Hybrid'),
        ],
        'source_type_options': [
            ('published_registry_dimension', 'Published Registry Dimension'),
            ('submission_fact', 'Submission Fact'),
            ('aggregated_submission_fact', 'Aggregated Submission Fact'),
            ('hybrid_fact_dimension', 'Hybrid Fact + Dimension'),
        ],
        'grain_options': [
            ('per_submission', 'Per Submission'),
            ('per_form_per_year', 'Per Form per Year'),
            ('per_scope_per_year', 'Per Scope per Year'),
            ('per_registry_record_per_year', 'Per Registry Record per Year'),
        ],
        'freshness_source_options': [
            ('submissions.submitted_at', 'submissions.submitted_at'),
            ('data_registry_versions.materialized_at', 'data_registry_versions.materialized_at'),
            ('hybrid_watermark', 'hybrid_watermark'),
        ],
        'freshness_strategy_options': [
            ('max_timestamp', 'max_timestamp'),
            ('source_watermark_compare', 'source_watermark_compare'),
            ('manual_assertion', 'manual_assertion'),
        ],
        'reporting_year_mode_options': [
            ('active_year', 'Active Year'),
            ('explicit', 'Explicit'),
            ('all_time', 'All Time'),
        ],
    }


def _get_active_report_version(report_item):
    if not report_item:
        return None
    return report_item.get('draft_version') or report_item.get('published_version')


def _build_report_viewer_options():
    return {
        'period_mode_labels': {
            'daily': 'Harian',
            'weekly': 'Mingguan',
            'monthly': 'Bulanan',
            'quarterly': 'Triwulan',
            'four_monthly': 'Caturwulan',
            'semester': 'Semester',
            'semesterly': 'Semester',
            'yearly': 'Tahunan',
        },
        'quick_preset_labels': {
            'last_7_days': '7 Hari Terakhir',
            'current_week': 'Minggu Ini',
            'last_30_days': '30 Hari Terakhir',
            'last_90_days': '90 Hari Terakhir',
            'current_month': 'Bulan Ini',
            'current_quarter': 'Triwulan Ini',
            'current_semester': 'Semester Ini',
            'current_year': 'Tahun Ini',
            'full_range': 'Semua Range',
        },
        'block_type_labels': {
            'metric_cards': 'Metric Cards',
            'plotly_timeseries': 'Plotly Timeseries',
            'detail_table': 'Detail Table',
            'geo_map': 'Geo Map',
            'narrative': 'Narrative',
        },
    }


def _serialize_report_viewer_config(report, active_version):
    structure = getattr(active_version, 'structure_json', None) or {}
    period_config = structure.get('period_preset_config', {}) or {}
    blocks = structure.get('blocks') or structure.get('block_definitions') or []
    return {
        'report_id': getattr(report, 'id', None),
        'report_key': getattr(report, 'report_key', None),
        'report_name': getattr(report, 'name', None),
        'report_version_id': getattr(active_version, 'id', None),
        'report_version_title': getattr(active_version, 'title', None),
        'meta_description': getattr(active_version, 'meta_description', None),
        'default_period_mode': period_config.get('default_mode', 'quarterly'),
        'supported_period_modes': period_config.get('supported_period_modes') or ['quarterly', 'semester', 'yearly'],
        'quick_presets': period_config.get('quick_presets') or ['current_quarter', 'current_semester', 'current_year'],
        'blocks': blocks,
    }


@analytics_web_bp.route('/analytics', methods=['GET'])
def analytics_workspace():
    """Menampilkan katalog dataset analytics sebagai entry point utama Domain 5."""

    error_message = None
    dataset_catalog_items = []
    total_datasets = 0
    total_published_versions = 0
    total_latest_runs = 0
    total_registry_links = 0

    try:
        query_service = AnalyticsQueryService()
        dataset_items = query_service.list_datasets()
        report_items = query_service.list_reports()

        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registry_items = _build_registry_browser_items(registry_service.repository.get_all(), version_service)

        dataset_catalog_items = _build_dataset_catalog_items(dataset_items, registry_items, report_items=report_items)
        total_datasets = len(dataset_catalog_items)
        total_published_versions = sum(1 for item in dataset_catalog_items if item.get('published_version'))
        total_latest_runs = sum(1 for item in dataset_catalog_items if item.get('latest_run'))
        total_registry_links = sum(item.get('linked_registry_count', 0) for item in dataset_catalog_items)
    except Exception as error:
        current_app.logger.error('Analytics dataset catalog error: %s', str(error))
        error_message = 'Gagal memuat katalog dataset analytics.'

    return render_template(
        'pages/analytics/index.html',
        dataset_items=dataset_catalog_items,
        total_datasets=total_datasets,
        total_published_versions=total_published_versions,
        total_latest_runs=total_latest_runs,
        total_registry_links=total_registry_links,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/registries', methods=['GET'])
def analytics_registry_linkage():
    """Menampilkan browser registry publish beserta keterkaitannya ke dataset analytics."""

    error_message = None
    published_registry_items = []

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
            published_registry_items.append(
                {
                    **item,
                    'related_dataset_count': len(related_datasets),
                    'related_dataset_items': related_datasets,
                }
            )
    except Exception as error:
        current_app.logger.error('Analytics registry linkage error: %s', str(error))
        error_message = 'Gagal memuat daftar linkage registry analytics.'

    return render_template(
        'pages/analytics/registries.html',
        registry_items=published_registry_items,
        total_published_registries=len(published_registry_items),
        total_related_datasets=sum(item.get('related_dataset_count', 0) for item in published_registry_items),
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/registries/<int:registry_id>/datasets', methods=['GET'])
@analytics_web_bp.route('/analytics/reports/<int:registry_id>', methods=['GET'])
def analytics_registry_datasets(registry_id):
    """Menampilkan daftar dataset analytics yang terkait dengan satu registry publish."""

    error_message = None
    registry_item = None
    related_dataset_items = []

    try:
        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registry_items = _build_registry_browser_items(registry_service.repository.get_all(), version_service)
        registry_item = _find_registry_by_id(registry_items, registry_id)
        if not registry_item:
            raise ValueError('Data registry tidak ditemukan.')

        related_dataset_items = _build_related_dataset_items(
            registry_item['registry'],
            AnalyticsQueryService().list_datasets(),
        )
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics registry dataset linkage detail error: %s', str(error))
        error_message = 'Gagal memuat dataset terkait registry analytics.'

    return render_template(
        'pages/analytics/registry_datasets.html',
        registry=registry_item.get('registry') if registry_item else None,
        draft_version=registry_item.get('draft_version') if registry_item else None,
        published_version=registry_item.get('published_version') if registry_item else None,
        related_dataset_items=related_dataset_items,
        related_dataset_count=len(related_dataset_items),
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/datasets/create', methods=['GET'])
def analytics_dataset_create():
    """Menampilkan builder dataset analytics agar flow source -> contract -> report eksplisit."""

    builder_options = _build_dataset_builder_options()
    return render_template(
        'pages/analytics/dataset_form.html',
        page_mode='create',
        dataset=None,
        active_version=None,
        linked_registries=[],
        builder_options=builder_options,
    )


@analytics_web_bp.route('/analytics/datasets/<int:dataset_id>/edit', methods=['GET'])
def analytics_dataset_edit(dataset_id):
    """Menampilkan builder edit dataset analytics untuk kontrak source, dimension, metric, dan report readiness."""

    error_message = None
    workspace = None
    linked_registry_items = []
    builder_options = _build_dataset_builder_options()

    try:
        query_service = AnalyticsQueryService()
        workspace = query_service.get_dataset_workspace(dataset_id)
        dataset_items = query_service.list_datasets()
        target_item = next((item for item in dataset_items if getattr(item.get('dataset'), 'id', None) == dataset_id), None)

        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registry_items = _build_registry_browser_items(registry_service.repository.get_all(), version_service)
        if target_item:
            linked_registry_items = _build_linked_registry_items(target_item, registry_items)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics dataset edit page error: %s', str(error))
        error_message = 'Gagal memuat editor dataset analytics.'

    dataset = (workspace or {}).get('dataset')
    active_version = (workspace or {}).get('draft_version') or (workspace or {}).get('published_version')

    return render_template(
        'pages/analytics/dataset_form.html',
        page_mode='edit',
        dataset=dataset,
        active_version=active_version,
        linked_registries=linked_registry_items,
        builder_options=builder_options,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/datasets/<int:dataset_id>', methods=['GET'])
def analytics_dataset_workspace(dataset_id):
    """Menampilkan workspace teknis dataset analytics: source, version, run, dan preview kontrak."""

    error_message = None
    workspace = None
    linked_registry_items = []
    latest_run = None
    linked_report_item = None

    try:
        query_service = AnalyticsQueryService()
        workspace = query_service.get_dataset_workspace(dataset_id)
        dataset_items = query_service.list_datasets()
        target_item = next((item for item in dataset_items if getattr(item.get('dataset'), 'id', None) == dataset_id), None)
        latest_run = target_item.get('latest_run') if target_item else None
        linked_report_item = next(
            (
                item for item in query_service.list_reports()
                if getattr(item.get('report'), 'dataset_id', None) == dataset_id
            ),
            None,
        )

        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registry_items = _build_registry_browser_items(registry_service.repository.get_all(), version_service)
        if target_item:
            linked_registry_items = _build_linked_registry_items(target_item, registry_items)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics dataset workspace error: %s', str(error))
        error_message = 'Gagal memuat workspace dataset analytics.'

    return render_template(
        'pages/analytics/dataset_workspace.html',
        dataset=(workspace or {}).get('dataset'),
        draft_version=(workspace or {}).get('draft_version'),
        published_version=(workspace or {}).get('published_version'),
        versions=(workspace or {}).get('versions') or [],
        runs=(workspace or {}).get('runs') or [],
        latest_run=latest_run,
        linked_report_item=linked_report_item,
        linked_registries=linked_registry_items,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/reports', methods=['GET'])
def analytics_report_index():
    """Menampilkan katalog report analytics semi-CMS yang terhubung ke dataset publish."""

    error_message = None
    report_items = []

    try:
        report_items = AnalyticsQueryService().list_reports()
    except Exception as error:
        current_app.logger.error('Analytics report catalog error: %s', str(error))
        error_message = 'Gagal memuat katalog report analytics.'

    return render_template(
        'pages/analytics/report_index.html',
        report_items=report_items,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/reports/create', methods=['GET'])
def analytics_report_create():
    """Menampilkan builder report semi-CMS yang wajib memilih dataset contract."""

    builder_options = _build_report_builder_options()
    dataset_items = []
    preselected_dataset = None
    dataset_id = None

    dataset_id = request.args.get('dataset_id', type=int)

    try:
        dataset_items = AnalyticsQueryService().list_datasets()
        if dataset_id is not None:
            preselected_dataset = next(
                (item for item in dataset_items if getattr(item.get('dataset'), 'id', None) == dataset_id),
                None,
            )
    except Exception as error:
        current_app.logger.error('Analytics report create page error: %s', str(error))

    return render_template(
        'pages/analytics/report_form.html',
        page_mode='create',
        report=None,
        active_version=None,
        dataset_items=dataset_items,
        preselected_dataset=preselected_dataset,
        builder_options=builder_options,
        error_message=None,
    )


@analytics_web_bp.route('/analytics/reports/<int:report_definition_id>/edit', methods=['GET'])
def analytics_report_edit(report_definition_id):
    """Menampilkan builder edit report semi-CMS yang terhubung eksplisit ke dataset."""

    error_message = None
    workspace = None
    dataset_items = []
    builder_options = _build_report_builder_options()

    try:
        query_service = AnalyticsQueryService()
        workspace = query_service.get_report_workspace(report_definition_id)
        dataset_items = query_service.list_datasets()
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics report edit page error: %s', str(error))
        error_message = 'Gagal memuat editor report analytics.'

    return render_template(
        'pages/analytics/report_form.html',
        page_mode='edit',
        report=(workspace or {}).get('report'),
        active_version=(workspace or {}).get('draft_version') or (workspace or {}).get('published_version'),
        dataset_items=dataset_items,
        preselected_dataset=None,
        builder_options=builder_options,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/datasets/<int:dataset_id>/report', methods=['GET'])
def analytics_dataset_report(dataset_id):
    """Menampilkan report viewer manusiawi berbasis dataset analytics, bukan langsung dari registry."""

    error_message = None
    workspace = None
    dataset_item = None
    linked_registry_items = []
    linked_report_item = None

    try:
        query_service = AnalyticsQueryService()
        workspace = query_service.get_dataset_workspace(dataset_id)
        dataset_items = query_service.list_datasets()
        dataset_item = next((item for item in dataset_items if getattr(item.get('dataset'), 'id', None) == dataset_id), None)
        linked_report_item = next(
            (
                item for item in query_service.list_reports()
                if getattr(item.get('report'), 'dataset_id', None) == dataset_id
            ),
            None,
        )

        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registry_items = _build_registry_browser_items(registry_service.repository.get_all(), version_service)
        if dataset_item:
            linked_registry_items = _build_linked_registry_items(dataset_item, registry_items)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics dataset report error: %s', str(error))
        error_message = 'Gagal memuat report dataset analytics.'

    dataset = (workspace or {}).get('dataset')
    draft_version = (workspace or {}).get('draft_version')
    published_version = (workspace or {}).get('published_version')
    active_version = draft_version or published_version
    primary_registry_item = linked_registry_items[0] if linked_registry_items else None
    primary_registry = primary_registry_item.get('registry') if primary_registry_item else None
    primary_registry_published_version = primary_registry_item.get('published_version') if primary_registry_item else None

    if dataset_item is None and dataset is not None:
        dataset_item = {
            'dataset': dataset,
            'draft_version': draft_version,
            'published_version': published_version,
            'latest_run': None,
        }

    active_report_version = _get_active_report_version(linked_report_item)
    report_viewer_options = _build_report_viewer_options()
    report_config = _serialize_report_viewer_config(
        linked_report_item.get('report') if linked_report_item else None,
        active_report_version,
    ) if linked_report_item and active_report_version else None

    workspace_config = {
        'analyticsDatasetsUrl': url_for('api_analytics_v1.list_dataset_definitions'),
        'analyticsDatasetDetailUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__',
        'analyticsDatasetRunsUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__/runs',
        'analyticsDatasetExecuteUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__/versions/__DATASET_VERSION_ID__/runs',
        'initialRegistry': _serialize_registry_summary(primary_registry, primary_registry_published_version),
        'initialDatasetId': getattr(dataset, 'id', None),
        'allowedDatasetIds': [getattr(dataset, 'id', None)] if getattr(dataset, 'id', None) is not None else [],
    }

    return render_template(
        'pages/analytics/detail_report.html',
        dataset=dataset,
        active_version=active_version,
        linked_registries=linked_registry_items,
        linked_registry_count=len(linked_registry_items),
        primary_registry=primary_registry,
        related_dataset_items=[dataset_item] if dataset_item else [],
        related_dataset_count=1 if dataset_item else 0,
        primary_dataset=dataset,
        linked_report_item=linked_report_item,
        active_report_version=active_report_version,
        report_config=report_config,
        report_viewer_options=report_viewer_options,
        workspace_config=workspace_config,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/registries/<int:registry_id>/metadata', methods=['GET'])
@analytics_web_bp.route('/analytics/reports/<int:registry_id>/metadata', methods=['GET'])
def analytics_registry_metadata(registry_id):
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
