import json

from flask import Blueprint, current_app, render_template, request, url_for

from app.modules.analytics.services import AnalyticsQueryService
from app.modules.data_registry.services import DataRegistryService, DataRegistryVersionService
from app.modules.form.models import Form, FormVersion


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
        'report_family_options': [
            ('custom', 'Custom / Fleksibel'),
            ('pk', 'Perjanjian Kinerja (PK)'),
            ('ik', 'Indikator Kinerja (IK)'),
            ('renaksi', 'Renaksi / Action Plan'),
            ('dashboard-eksekutif', 'Dashboard Eksekutif'),
        ],
        'report_type_options': [
            ('custom', 'Custom / Flexible Report'),
            ('scorecard', 'Scorecard / KPI'),
            ('monitoring', 'Monitoring'),
            ('pk', 'PK Structured Report'),
            ('renaksi', 'Renaksi Structured Report'),
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
        'report_type_aliases': {
            'custom_report': 'custom',
            'performance_report': 'scorecard',
            'narrative_report': 'monitoring',
            'geo_report': 'monitoring',
        },
    }


def _infer_builder_curated_field_role(key, field_type, source_name):
    normalized_key = str(key or '').strip().lower()
    normalized_type = str(field_type or '').strip().lower()
    if normalized_key in {'tanggal', 'date', 'submitted_at', 'period_date'} or normalized_type in {'date', 'datetime'}:
        return 'date'
    if normalized_key in {'latitude', 'lat'} or 'latitude' in normalized_key:
        return 'geo_latitude'
    if normalized_key in {'longitude', 'lng', 'lon'} or 'longitude' in normalized_key:
        return 'geo_longitude'
    if source_name == 'metric':
        return 'metric'
    if source_name == 'dimension':
        return 'dimension'
    if normalized_type in {'integer', 'number', 'numeric', 'float', 'decimal'} and any(
        token in normalized_key for token in ['total', 'jumlah', 'count', 'pct', 'percent', 'achievement', 'score', 'target', 'realisasi', 'capaian', 'deviasi', 'progres', 'progress', 'nilai']
    ):
        return 'metric'
    return 'dimension'


def _build_builder_curated_fields(dataset_version):
    curated_fields = []
    seen_keys = set()
    metric_keys = _extract_builder_field_keys(getattr(dataset_version, 'metric_definitions_json', None) or [])
    dimension_keys = _extract_builder_field_keys(getattr(dataset_version, 'dimension_definitions_json', None) or [])
    field_groups = [
        ('output_schema', getattr(dataset_version, 'output_schema_json', None) or []),
        ('dimension', getattr(dataset_version, 'dimension_definitions_json', None) or []),
        ('metric', getattr(dataset_version, 'metric_definitions_json', None) or []),
    ]
    for source_name, field_defs in field_groups:
        for field in field_defs:
            field_payload = field if isinstance(field, dict) else {'key': field}
            key = field_payload.get('key') or field_payload.get('field_key') or field_payload.get('name')
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            field_type = field_payload.get('type') or field_payload.get('data_type') or 'string'
            role_source_name = _resolve_builder_curated_role_source(key, source_name, metric_keys, dimension_keys)
            curated_fields.append(
                {
                    'key': key,
                    'label': field_payload.get('label') or field_payload.get('title') or key.replace('_', ' ').title(),
                    'type': field_type,
                    'source': source_name,
                    'role': _infer_builder_curated_field_role(key, field_type, role_source_name),
                }
            )
    return curated_fields


def _extract_builder_field_keys(field_defs):
    keys = set()
    for field in field_defs:
        field_payload = field if isinstance(field, dict) else {'key': field}
        key = field_payload.get('key') or field_payload.get('field_key') or field_payload.get('name')
        if key:
            keys.add(key)
    return keys


def _resolve_builder_curated_role_source(key, source_name, metric_keys, dimension_keys):
    if key in metric_keys:
        return 'metric'
    if key in dimension_keys:
        return 'dimension'
    return source_name


def _serialize_dataset_run_for_report_builder(run):
    if not run:
        return None
    # AnalyticsDatasetRun stores materialized output in `summary_json` and
    # `result_preview_json`. Older tests/stubs used `result_summary_json`, so
    # keep that as a compatibility fallback. The item report builder needs real
    # preview rows here to derive categorical value options such as
    # status_realisasi -> belum_jalan/proses/selesai.
    result_summary = (
        getattr(run, 'summary_json', None)
        or getattr(run, 'result_summary_json', None)
        or {}
    )
    row_snapshots = (
        result_summary.get('row_snapshots')
        or getattr(run, 'result_preview_json', None)
        or []
    )
    return {
        'id': getattr(run, 'id', None),
        'status': getattr(run, 'status', None),
        'result_row_count': getattr(run, 'result_row_count', None),
        # Report item KPI builder menghitung distinct value dan count dari rows ini.
        # Jangan dipotong seperti preview tabel, agar count field/value tetap sesuai
        # latest run materialized rows (contoh harmon-2026 punya 104 row).
        'row_snapshots': row_snapshots,
        'summary': {
            'row_count': result_summary.get('row_count'),
            'completion': result_summary.get('completion') or {},
        },
    }


def _serialize_dataset_version_for_report_builder(dataset, dataset_version, variant):
    if not dataset_version:
        return None
    return {
        'id': getattr(dataset_version, 'id', None),
        'variant': variant,
        'status': getattr(dataset_version, 'status', None),
        'version_number': getattr(dataset_version, 'version_number', None),
        'label': f"{getattr(dataset, 'name', 'Dataset')} — {'Draft' if variant == 'draft' else 'Publish'} v{getattr(dataset_version, 'version_number', '-')}",
        'curated_fields': _build_builder_curated_fields(dataset_version),
        'latest_run': _serialize_dataset_run_for_report_builder(getattr(dataset_version, 'latest_run', None)),
    }


def _build_report_builder_dataset_catalog(dataset_items):
    catalog = []
    for item in dataset_items or []:
        dataset = item.get('dataset')
        if not dataset:
            continue
        versions = []
        draft_version = _serialize_dataset_version_for_report_builder(dataset, item.get('draft_version'), 'draft')
        published_version = _serialize_dataset_version_for_report_builder(dataset, item.get('published_version'), 'published')
        latest_run_payload = _serialize_dataset_run_for_report_builder(item.get('latest_run'))
        if draft_version:
            draft_version['latest_run'] = draft_version.get('latest_run') or latest_run_payload
            versions.append(draft_version)
        if published_version:
            published_version['latest_run'] = published_version.get('latest_run') or latest_run_payload
            versions.append(published_version)
        catalog.append(
            {
                'id': getattr(dataset, 'id', None),
                'dataset_key': getattr(dataset, 'dataset_key', None),
                'name': getattr(dataset, 'name', None),
                'source_domain': getattr(dataset, 'source_domain', None),
                'source_type': getattr(dataset, 'source_type', None),
                'versions': versions,
            }
        )
    return catalog


def _extract_formio_fields(schema):
    """Ambil field importable dari schema Form.io untuk wizard dataset manusiawi."""

    fields = []

    def collect_nested_components(value):
        """Normalisasi nested Form.io containers tanpa menganggap `rows` selalu layout iterable."""

        nested = []
        if isinstance(value, dict):
            components = value.get('components')
            if isinstance(components, list):
                nested.extend(components)
            else:
                nested.append(value)
            return nested
        if isinstance(value, list):
            for item in value:
                nested.extend(collect_nested_components(item))
        return nested

    def walk(components):
        for component in components or []:
            if not isinstance(component, dict):
                continue
            nested = []
            nested.extend(collect_nested_components(component.get('components')))
            columns = component.get('columns')
            for column in columns if isinstance(columns, list) else []:
                if isinstance(column, dict):
                    nested.extend(collect_nested_components(column.get('components')))
            rows = component.get('rows')
            if isinstance(rows, list):
                # `rows` pada layout/table Form.io bisa list dua dimensi, sedangkan
                # `rows` pada textarea adalah integer konfigurasi tinggi input.
                nested.extend(collect_nested_components(rows))
            if nested:
                walk(nested)
            key = component.get('key')
            component_type = component.get('type')
            if not key or component_type in {'button', 'htmlelement', 'content'}:
                continue
            fields.append(
                {
                    'key': key,
                    'label': component.get('label') or key.replace('_', ' ').title(),
                    'type': component_type or 'string',
                }
            )

    walk((schema or {}).get('components') or [])
    seen = set()
    unique_fields = []
    for field in fields:
        if field['key'] in seen:
            continue
        seen.add(field['key'])
        unique_fields.append(field)
    return unique_fields


def _build_source_form_options():
    """Menyediakan katalog form published agar dataset builder tidak mulai dari JSON kosong."""

    try:
        rows = (
            Form.query.join(FormVersion, FormVersion.form_id == Form.id)
            .filter(Form.deleted_at == None, FormVersion.deleted_at == None, FormVersion.is_published == True)
            .order_by(Form.name.asc(), FormVersion.version_number.desc())
            .all()
        )
    except Exception as error:
        current_app.logger.warning('Gagal memuat source form options untuk dataset builder: %s', str(error))
        return []

    options = []
    seen_form_ids = set()
    for form in rows:
        if form.id in seen_form_ids:
            continue
        seen_form_ids.add(form.id)
        published_versions = [
            version for version in getattr(form, 'versions', []) or []
            if getattr(version, 'is_published', False) and not getattr(version, 'deleted_at', None)
        ]
        if not published_versions:
            continue
        published_version = sorted(published_versions, key=lambda version: version.version_number, reverse=True)[0]
        options.append(
            {
                'id': form.id,
                'code': form.code,
                'name': form.name,
                'version_id': published_version.id,
                'version_number': published_version.version_number,
                'fields': _extract_formio_fields(published_version.schema or {}),
            }
        )
    return options


def _build_dataset_builder_options():
    return {
        'source_form_options': _build_source_form_options(),
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
        'report_family_labels': {
            'custom': 'Custom / Fleksibel',
            'pk': 'Perjanjian Kinerja (PK)',
            'ik': 'Indikator Kinerja (IK)',
            'renaksi': 'Renaksi / Action Plan',
            'dashboard-eksekutif': 'Dashboard Eksekutif',
        },
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
            'dimension_distribution': 'Dimension Distribution',
            'detail_table': 'Detail Table',
            'geo_map': 'Geo Map',
            'narrative': 'Narrative',
        },
    }


def _collect_report_selected_indicator_keys(blocks):
    selected_keys = set()
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        config = block.get('config') or {}
        for key in config.get('metric_keys') or []:
            if key:
                selected_keys.add(str(key))
        for key in config.get('focus_field_keys') or []:
            if key:
                selected_keys.add(str(key))
        for series in config.get('series') or []:
            if isinstance(series, dict) and series.get('key'):
                selected_keys.add(str(series['key']))
    return sorted(selected_keys)


def _serialize_report_viewer_config(report, active_version):
    structure = getattr(active_version, 'structure_json', None) or {}
    period_config = structure.get('period_preset_config', {}) or {}
    raw_blocks = structure.get('blocks') or structure.get('block_definitions') or []
    blocks = sorted(
        list(raw_blocks),
        key=lambda block: (block or {}).get('order', 9999) if isinstance(block, dict) else 9999,
    )
    report_settings = getattr(report, 'settings_json', None) or {}
    report_family = report_settings.get('report_family') or 'custom'
    selected_indicator_keys = _collect_report_selected_indicator_keys(blocks)
    return {
        'report_id': getattr(report, 'id', None),
        'report_key': getattr(report, 'report_key', None),
        'report_name': getattr(report, 'name', None),
        'report_family': report_family,
        'report_version_id': getattr(active_version, 'id', None),
        'report_version_title': getattr(active_version, 'title', None),
        'meta_description': getattr(active_version, 'meta_description', None),
        'default_period_mode': period_config.get('default_mode', 'quarterly'),
        'supported_period_modes': period_config.get('supported_period_modes') or ['quarterly', 'semester', 'yearly'],
        'quick_presets': period_config.get('quick_presets') or ['current_quarter', 'current_semester', 'current_year'],
        'dataset_contract': structure.get('dataset_contract') or {},
        'data_sources': structure.get('data_sources') or [],
        'narrative_guidance': getattr(active_version, 'narrative_guidance_json', None) or {},
        'selected_indicator_keys': selected_indicator_keys,
        'selected_indicator_count': len(selected_indicator_keys),
        'blocks': blocks,
    }


def _serialize_dataset_statistics_config(dataset, active_version):
    curated_fields = _build_builder_curated_fields(active_version) if active_version else []
    metric_fields = [field for field in curated_fields if field.get('role') == 'metric']
    dimension_fields = [field for field in curated_fields if field.get('role') == 'dimension']
    date_fields = [field for field in curated_fields if field.get('role') == 'date']
    all_field_keys = [field.get('key') for field in curated_fields if field.get('key')]
    metric_keys = [field.get('key') for field in metric_fields if field.get('key')]
    dimension_keys = [field.get('key') for field in dimension_fields if field.get('key')]
    selectable_dimension_keys = [
        field.get('key') for field in dimension_fields
        if field.get('key') and str(field.get('type') or '').lower() in {'select', 'radio', 'checkbox', 'selectboxes'}
    ]
    chart_dimension_keys = selectable_dimension_keys or dimension_keys
    date_key = (date_fields[0].get('key') if date_fields else None) or ''
    series_keys = metric_keys[:3] or ['total']
    table_columns = all_field_keys[:8]
    return {
        'report_id': None,
        'report_key': 'dataset-statistics',
        'report_name': 'Statistik Dataset',
        'report_family': 'dataset_statistics',
        'report_version_id': None,
        'report_version_title': 'Statistik Dataset',
        'meta_description': 'Statistik dataset menampilkan chart, tabel data hasil run, preset waktu, dan export tanpa bergantung pada report semi-CMS.',
        'default_period_mode': 'monthly',
        'supported_period_modes': ['weekly', 'monthly', 'quarterly', 'semester', 'yearly'],
        'quick_presets': ['current_week', 'current_month', 'current_quarter', 'current_semester', 'current_year', 'full_range'],
        'dataset_contract': {
            'dataset_id': getattr(dataset, 'id', None),
            'dataset_key': getattr(dataset, 'dataset_key', None),
            'dataset_version_id': getattr(active_version, 'id', None),
            'dataset_version_number': getattr(active_version, 'version_number', None),
            'curated_fields': curated_fields,
            'run_binding': {
                'dataset_id': getattr(dataset, 'id', None),
                'dataset_key': getattr(dataset, 'dataset_key', None),
                'dataset_version_id': getattr(active_version, 'id', None),
                'dataset_version_number': getattr(active_version, 'version_number', None),
                'selection_mode': 'latest_succeeded_run',
            },
        },
        'data_sources': [
            {
                'alias': 'primary',
                'label': getattr(dataset, 'name', None) or 'Dataset utama',
                'dataset_id': getattr(dataset, 'id', None),
                'dataset_key': getattr(dataset, 'dataset_key', None),
                'dataset_name': getattr(dataset, 'name', None),
                'dataset_version_id': getattr(active_version, 'id', None),
                'dataset_version_number': getattr(active_version, 'version_number', None),
                'selection_mode': 'latest_succeeded_run',
                'curated_fields': curated_fields,
            }
        ] if dataset and active_version else [],
        'narrative_guidance': {},
        'selected_indicator_keys': sorted(set(all_field_keys)),
        'selected_indicator_count': len(set(all_field_keys)),
        'blocks': [
            {'type': 'metric_cards', 'title': 'KPI Statistik Dataset', 'data_source_alias': 'primary', 'order': 1, 'config': {'metric_keys': metric_keys[:4] or ['total']}},
            {'type': 'plotly_timeseries', 'title': 'Chart Waktu Dataset', 'data_source_alias': 'primary', 'order': 2, 'config': {'x_key': date_key, 'series': [{'key': key, 'label': key.replace('_', ' ').title(), 'aggregation': 'sum'} for key in series_keys]}},
            {'type': 'dimension_distribution', 'title': 'Chart Dimensi Select', 'data_source_alias': 'primary', 'order': 3, 'config': {'dimension_keys': chart_dimension_keys, 'measure_key': 'total', 'top_n': 20}},
            {'type': 'detail_table', 'title': 'Tabel Data Hasil Run', 'data_source_alias': 'primary', 'order': 4, 'config': {'column_keys': table_columns}},
            {'type': 'narrative', 'title': 'Narasi Statistik Otomatis', 'data_source_alias': 'primary', 'order': 5, 'config': {'focus_field_keys': metric_keys[:3] or ['total'], 'source_mode': 'auto_summary'}},
        ],
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
        linked_report_item=None,
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
        builder_dataset_catalog=_build_report_builder_dataset_catalog(dataset_items),
        preselected_dataset=preselected_dataset,
        builder_options=builder_options,
        error_message=None,
    )


@analytics_web_bp.route('/analytics/datasets/<int:dataset_id>/report', methods=['GET'])
def analytics_dataset_report_builder(dataset_id):
    """Shortcut lama dari dataset menuju Builder Report multi dataset dengan source awal terpilih."""

    builder_options = _build_report_builder_options()
    dataset_items = []
    preselected_dataset = None
    workspace = None
    error_message = None

    try:
        query_service = AnalyticsQueryService()
        dataset_items = query_service.list_datasets()
        preselected_dataset = next(
            (item for item in dataset_items if getattr(item.get('dataset'), 'id', None) == dataset_id),
            None,
        )
        linked_report_item = next(
            (
                item for item in query_service.list_reports()
                if getattr(item.get('report'), 'dataset_id', None) == dataset_id
            ),
            None,
        )
        if linked_report_item and linked_report_item.get('report'):
            workspace = query_service.get_report_workspace(linked_report_item['report'].id)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error('Analytics dataset report builder shortcut error: %s', str(error))
        error_message = 'Gagal memuat builder report dataset.'

    if workspace:
        return render_template(
            'pages/analytics/report_form.html',
            page_mode='edit',
            report=workspace.get('report'),
            active_version=workspace.get('draft_version') or workspace.get('published_version'),
            dataset_items=dataset_items,
            builder_dataset_catalog=_build_report_builder_dataset_catalog(dataset_items),
            preselected_dataset=preselected_dataset,
            builder_options=builder_options,
            error_message=error_message,
        )

    return render_template(
        'pages/analytics/report_form.html',
        page_mode='create',
        report=None,
        active_version=None,
        dataset_items=dataset_items,
        builder_dataset_catalog=_build_report_builder_dataset_catalog(dataset_items),
        preselected_dataset=preselected_dataset,
        builder_options=builder_options,
        error_message=error_message,
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
        builder_dataset_catalog=_build_report_builder_dataset_catalog(dataset_items),
        preselected_dataset=None,
        builder_options=builder_options,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/reports/<int:report_definition_id>/items/<int:item_id>/edit', methods=['GET'])
def analytics_report_item_edit(report_definition_id, item_id):
    """Menampilkan editor item/indikator report: dataset, metric capaian, target, chart, tabel, dan manual input."""

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
        current_app.logger.error('Analytics report item edit page error: %s', str(error))
        error_message = 'Gagal memuat editor item report analytics.'

    active_version = (workspace or {}).get('draft_version') or (workspace or {}).get('published_version')
    structure = getattr(active_version, 'structure_json', None) or {}
    report_items = structure.get('report_items') or []
    zero_based_index = max((item_id or 1) - 1, 0)
    report_item = report_items[zero_based_index] if zero_based_index < len(report_items) else {
        'name': f'Indikator {item_id}',
        'item_key': f'indikator-{item_id}',
        'datasets': [],
    }

    return render_template(
        'pages/analytics/report_item_form.html',
        report=(workspace or {}).get('report'),
        active_version=active_version,
        report_item=report_item,
        item_index=zero_based_index,
        dataset_items=dataset_items,
        builder_dataset_catalog=_build_report_builder_dataset_catalog(dataset_items),
        builder_options=builder_options,
        error_message=error_message,
    )


@analytics_web_bp.route('/analytics/datasets/<int:dataset_id>/statistics', methods=['GET'])
def analytics_dataset_statistics(dataset_id):
    """Menampilkan statistik dataset: chart, tabel data, export, dan preset waktu."""

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
        current_app.logger.error('Analytics dataset statistics error: %s', str(error))
        error_message = 'Gagal memuat statistik dataset analytics.'

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

    active_report_version = None
    report_viewer_options = _build_report_viewer_options()
    report_config = _serialize_dataset_statistics_config(dataset, active_version)

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
        'pages/analytics/dataset_statistics.html',
        dataset=dataset,
        active_version=active_version,
        linked_registries=linked_registry_items,
        linked_registry_count=len(linked_registry_items),
        primary_registry=primary_registry,
        related_dataset_items=[dataset_item] if dataset_item else [],
        related_dataset_count=1 if dataset_item else 0,
        primary_dataset=dataset,
        linked_report_item=None,
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
