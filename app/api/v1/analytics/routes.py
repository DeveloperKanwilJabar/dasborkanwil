from flask import Blueprint, current_app, request
from flasgger import swag_from
from flask_login import current_user

from app.api.docs import (
    build_spec,
    envelope_schema,
    path_parameter,
    query_parameter,
    standard_responses,
)
from app.core.extensions import db
from app.core.utils import json_response
from app.modules.analytics.services import (
    AnalyticsDatasetRunService,
    AnalyticsDatasetService,
    AnalyticsIndicatorResultService,
    AnalyticsIndicatorService,
    AnalyticsQueryService,
    AnalyticsReportService,
)


api_analytics_bp = Blueprint(
    'api_analytics_v1',
    __name__,
    url_prefix='/api/v1/analytics',
)

LIST_DATASETS_DOC = build_spec(
    tag='Analytics',
    summary='Ambil daftar analytics dataset workspace.',
    description='Mengembalikan daftar dataset beserta draft/published version dan latest run untuk workspace analytics.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Daftar analytics dataset berhasil diambil.'), 'Daftar analytics dataset berhasil diambil.'),
)
GET_DATASET_WORKSPACE_DOC = build_spec(
    tag='Analytics',
    summary='Ambil detail satu dataset workspace.',
    description='Dipakai untuk memuat detail dataset, daftar version, dan daftar run terbaru.',
    parameters=[path_parameter('dataset_id', description='ID dataset analytics.', example=77)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Detail analytics dataset berhasil diambil.'), 'Detail analytics dataset berhasil diambil.'),
)
LIST_DATASET_RUNS_DOC = build_spec(
    tag='Analytics',
    summary='Ambil daftar run untuk satu dataset.',
    description='Mengembalikan history run dataset berdasarkan dataset_id.',
    parameters=[path_parameter('dataset_id', description='ID dataset analytics.', example=77)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Daftar analytics dataset run berhasil diambil.'), 'Daftar analytics dataset run berhasil diambil.'),
)
GET_DATASET_RUN_DETAIL_DOC = build_spec(
    tag='Analytics',
    summary='Ambil detail satu dataset run.',
    description='Menampilkan status run, freshness, preview result, dan error metadata bila ada.',
    parameters=[path_parameter('run_id', description='ID run dataset.', example=900)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Detail analytics dataset run berhasil diambil.'), 'Detail analytics dataset run berhasil diambil.'),
)
CREATE_DATASET_RUN_DOC = build_spec(
    tag='Analytics',
    summary='Mulai dataset run baru.',
    description='Menjalankan query/transform dataset pada version tertentu dengan filter request opsional.',
    parameters=[path_parameter('dataset_id', description='ID dataset analytics.', example=77), path_parameter('dataset_version_id', description='ID dataset version yang akan dijalankan.', example=78)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics dataset run berhasil masuk antrean refresh.'), 'Analytics dataset run berhasil masuk antrean refresh.', success_status=202),
)
CREATE_DATASET_DOC = build_spec(
    tag='Analytics',
    summary='Buat analytics dataset beserta draft contract awal.',
    description='Membuat definition dataset lalu langsung menyiapkan draft version pertamanya agar source picker, selected fields, dimension, metric, dan report readiness bisa dikelola sebagai satu flow.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics dataset berhasil dibuat.'), 'Analytics dataset berhasil dibuat.', success_status=201),
)
UPDATE_DATASET_DOC = build_spec(
    tag='Analytics',
    summary='Perbarui analytics dataset dan draft contract aktif.',
    description='Mengubah metadata dataset lalu meng-update draft version aktif. Bila draft belum ada, backend akan membuat draft baru tanpa merusak versi published sebelumnya.',
    parameters=[path_parameter('dataset_id', description='ID dataset analytics.', example=77)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics dataset berhasil diperbarui.'), 'Analytics dataset berhasil diperbarui.'),
)
PUBLISH_DATASET_VERSION_DOC = build_spec(
    tag='Analytics',
    summary='Publish dataset version.',
    description='Mempublish draft contract dataset agar siap dipakai dataset run dan report dinamis.',
    parameters=[path_parameter('version_id', description='ID dataset version.', example=78)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics dataset version berhasil dipublish.'), 'Analytics dataset version berhasil dipublish.'),
)
LIST_REPORTS_DOC = build_spec(
    tag='Analytics',
    summary='Ambil daftar analytics report.',
    description='Mengembalikan daftar report definition untuk workspace analytics.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Daftar analytics report berhasil diambil.'), 'Daftar analytics report berhasil diambil.'),
)
GET_REPORT_WORKSPACE_DOC = build_spec(
    tag='Analytics',
    summary='Ambil detail satu report workspace.',
    description='Memuat report definition, version, dan mapping indikator yang terpasang.',
    parameters=[path_parameter('report_definition_id', description='ID report definition.', example=21)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Detail analytics report berhasil diambil.'), 'Detail analytics report berhasil diambil.'),
)
LIST_INDICATORS_DOC = build_spec(
    tag='Analytics',
    summary='Ambil daftar analytics indicator.',
    description='Mengembalikan daftar indikator dan snapshot workspace-nya.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Daftar analytics indicator berhasil diambil.'), 'Daftar analytics indicator berhasil diambil.'),
)
GET_INDICATOR_WORKSPACE_DOC = build_spec(
    tag='Analytics',
    summary='Ambil detail satu indicator workspace.',
    description='Memuat definition, version, result history, dan progress entries indikator.',
    parameters=[path_parameter('indicator_definition_id', description='ID indicator definition.', example=41)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Detail analytics indicator berhasil diambil.'), 'Detail analytics indicator berhasil diambil.'),
)
LIST_INDICATOR_RESULTS_DOC = build_spec(
    tag='Analytics',
    summary='Ambil daftar indicator result.',
    description='Mendukung filter indicator_version_id, reporting_year, reporting_period_id, dan limit.',
    parameters=[query_parameter('indicator_version_id', value_type='integer', description='Filter version indikator.', example=51), query_parameter('reporting_year', value_type='integer', description='Filter tahun.', example=2026), query_parameter('reporting_period_id', value_type='integer', description='Filter period.', example=3), query_parameter('limit', value_type='integer', description='Batas hasil.', example=50, default=50)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Daftar analytics indicator result berhasil diambil.'), 'Daftar analytics indicator result berhasil diambil.'),
)
CREATE_REPORT_DOC = build_spec(
    tag='Analytics',
    summary='Buat report analytics beserta draft builder awal.',
    description='Membuat definisi report yang terhubung ke dataset lalu langsung menyiapkan draft semi-CMS berisi block, preset periode, filter schema, dan narrative guidance.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics report berhasil dibuat.'), 'Analytics report berhasil dibuat.', success_status=201),
)
UPDATE_REPORT_DOC = build_spec(
    tag='Analytics',
    summary='Perbarui report analytics dan draft builder aktif.',
    description='Mengubah metadata report, relasi dataset, dataset version, serta schema builder report seperti block/layout/filter/preset periode tanpa perlu scroll ke metadata terpisah.',
    parameters=[path_parameter('report_definition_id', description='ID report definition.', example=21)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics report berhasil diperbarui.'), 'Analytics report berhasil diperbarui.'),
)
CREATE_REPORT_VERSION_DOC = build_spec(
    tag='Analytics',
    summary='Buat report version baru.',
    description='Membuat draft version untuk report definition tertentu.',
    parameters=[path_parameter('report_definition_id', description='ID report definition.', example=21)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics report version berhasil dibuat.'), 'Analytics report version berhasil dibuat.', success_status=201),
)
PUBLISH_REPORT_VERSION_DOC = build_spec(
    tag='Analytics',
    summary='Publish report version.',
    description='Mempublish satu report version agar menjadi referensi aktif workspace report.',
    parameters=[path_parameter('version_id', description='ID report version.', example=31)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics report version berhasil dipublish.'), 'Analytics report version berhasil dipublish.'),
)
CREATE_INDICATOR_DOC = build_spec(
    tag='Analytics',
    summary='Buat indicator definition baru.',
    description='Membuat definisi indikator analytics baru.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics indicator berhasil dibuat.'), 'Analytics indicator berhasil dibuat.', success_status=201),
)
CREATE_INDICATOR_VERSION_DOC = build_spec(
    tag='Analytics',
    summary='Buat indicator version baru.',
    description='Membuat draft version untuk indikator, termasuk formula/target/dataset contract.',
    parameters=[path_parameter('indicator_definition_id', description='ID indicator definition.', example=41)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics indicator version berhasil dibuat.'), 'Analytics indicator version berhasil dibuat.', success_status=201),
)
PUBLISH_INDICATOR_VERSION_DOC = build_spec(
    tag='Analytics',
    summary='Publish indicator version.',
    description='Mempublish satu indicator version menjadi versi aktif.',
    parameters=[path_parameter('version_id', description='ID indicator version.', example=51)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics indicator version berhasil dipublish.'), 'Analytics indicator version berhasil dipublish.'),
)
ATTACH_INDICATOR_TO_REPORT_DOC = build_spec(
    tag='Analytics',
    summary='Pasang indicator ke report version.',
    description='Membuat mapping indikator ke suatu report version beserta urutan/label tampilannya.',
    parameters=[path_parameter('report_version_id', description='ID report version.', example=31)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Indicator berhasil di-attach ke report version.'), 'Indicator berhasil di-attach ke report version.', success_status=201),
)
RECORD_INDICATOR_RESULT_DOC = build_spec(
    tag='Analytics',
    summary='Simpan indicator result.',
    description='Merekam hasil ukur indikator untuk periode/tahun tertentu.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics indicator result berhasil disimpan.'), 'Analytics indicator result berhasil disimpan.', success_status=201),
)
RECORD_PROGRESS_ENTRY_DOC = build_spec(
    tag='Analytics',
    summary='Simpan indicator progress entry.',
    description='Merekam progres kualitatif/operasional indikator pada periode tertentu.',
    parameters=[],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics indicator progress entry berhasil disimpan.'), 'Analytics indicator progress entry berhasil disimpan.', success_status=201),
)
SYNC_RESULT_FROM_PROGRESS_DOC = build_spec(
    tag='Analytics',
    summary='Sinkronkan result dari progress entry.',
    description='Menghitung atau menyalin result indikator berdasarkan progress entry tertentu.',
    parameters=[path_parameter('progress_entry_id', description='ID progress entry.', example=81)],
    responses=standard_responses(envelope_schema({'type': 'object'}, message_example='Analytics indicator result berhasil disinkronkan dari progress.'), 'Analytics indicator result berhasil disinkronkan dari progress.'),
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


def current_actor():
    if current_user and not getattr(current_user, 'is_anonymous', True):
        return current_user
    return None


def iso_or_none(value):
    return value.isoformat() if value else None


def serialize_report_definition(report):
    if not report:
        return None
    if isinstance(report, dict):
        return report
    return {
        'id': report.id,
        'uuid': report.uuid,
        'report_key': report.report_key,
        'dataset_id': getattr(report, 'dataset_id', None),
        'name': report.name,
        'description': report.description,
        'report_type': report.report_type,
        'category_key': report.category_key,
        'status': report.status,
        'is_active': report.is_active,
        'settings_json': getattr(report, 'settings_json', {}) or {},
        'tags_json': getattr(report, 'tags_json', []) or [],
        'created_at': iso_or_none(getattr(report, 'created_at', None)),
        'updated_at': iso_or_none(getattr(report, 'updated_at', None)),
    }


def serialize_report_version(version):
    if not version:
        return None
    if isinstance(version, dict):
        return version
    return {
        'id': version.id,
        'uuid': version.uuid,
        'report_definition_id': version.report_definition_id,
        'version_number': version.version_number,
        'dataset_version_id': getattr(version, 'dataset_version_id', None),
        'status': version.status,
        'is_current_draft': version.is_current_draft,
        'is_current_published': version.is_current_published,
        'title': version.title,
        'meta_description': getattr(version, 'meta_description', None),
        'structure_json': getattr(version, 'structure_json', {}) or {},
        'narrative_guidance_json': getattr(version, 'narrative_guidance_json', {}) or {},
        'published_at': iso_or_none(getattr(version, 'published_at', None)),
        'created_at': iso_or_none(getattr(version, 'created_at', None)),
        'updated_at': iso_or_none(getattr(version, 'updated_at', None)),
    }


def serialize_indicator_definition(indicator):
    if not indicator:
        return None
    if isinstance(indicator, dict):
        return indicator
    return {
        'id': indicator.id,
        'uuid': indicator.uuid,
        'indicator_key': indicator.indicator_key,
        'indicator_code': getattr(indicator, 'indicator_code', None),
        'name': indicator.name,
        'description': indicator.description,
        'source_mode': indicator.source_mode,
        'calculation_type': indicator.calculation_type,
        'target_source_type': indicator.target_source_type,
        'status': indicator.status,
        'is_active': indicator.is_active,
        'settings_json': getattr(indicator, 'settings_json', {}) or {},
        'tags_json': getattr(indicator, 'tags_json', []) or [],
        'created_at': iso_or_none(getattr(indicator, 'created_at', None)),
        'updated_at': iso_or_none(getattr(indicator, 'updated_at', None)),
    }


def serialize_indicator_version(version):
    if not version:
        return None
    if isinstance(version, dict):
        return version
    return {
        'id': version.id,
        'uuid': version.uuid,
        'indicator_definition_id': version.indicator_definition_id,
        'version_number': version.version_number,
        'dataset_id': getattr(version, 'dataset_id', None),
        'dataset_version_id': getattr(version, 'dataset_version_id', None),
        'status': version.status,
        'is_current_draft': version.is_current_draft,
        'is_current_published': version.is_current_published,
        'period_mode': version.period_mode,
        'aggregation_strategy': version.aggregation_strategy,
        'unit_label': getattr(version, 'unit_label', None),
        'meta_description': getattr(version, 'meta_description', None),
        'formula_json': getattr(version, 'formula_json', {}) or {},
        'target_config_json': getattr(version, 'target_config_json', {}) or {},
        'narrative_guidance_json': getattr(version, 'narrative_guidance_json', {}) or {},
        'threshold_rules_json': getattr(version, 'threshold_rules_json', []) or [],
        'published_at': iso_or_none(getattr(version, 'published_at', None)),
        'created_at': iso_or_none(getattr(version, 'created_at', None)),
        'updated_at': iso_or_none(getattr(version, 'updated_at', None)),
    }


def serialize_report_mapping(mapping):
    if not mapping:
        return None
    if isinstance(mapping, dict):
        return mapping
    return {
        'id': mapping.id,
        'uuid': mapping.uuid,
        'report_version_id': mapping.report_version_id,
        'indicator_version_id': mapping.indicator_version_id,
        'item_order': mapping.item_order,
        'display_label': getattr(mapping, 'display_label', None),
        'section_key': getattr(mapping, 'section_key', None),
        'config_json': getattr(mapping, 'config_json', {}) or {},
        'created_at': iso_or_none(getattr(mapping, 'created_at', None)),
        'updated_at': iso_or_none(getattr(mapping, 'updated_at', None)),
    }


def serialize_indicator_result(result):
    if not result:
        return None
    if isinstance(result, dict):
        return result
    return {
        'id': result.id,
        'uuid': result.uuid,
        'indicator_version_id': result.indicator_version_id,
        'dataset_run_id': getattr(result, 'dataset_run_id', None),
        'reporting_year': getattr(result, 'reporting_year', None),
        'reporting_period_id': getattr(result, 'reporting_period_id', None),
        'status': result.status,
        'completion_status': result.completion_status,
        'measured_value': None if getattr(result, 'measured_value', None) is None else str(result.measured_value),
        'target_value': None if getattr(result, 'target_value', None) is None else str(result.target_value),
        'achievement_percentage': None if getattr(result, 'achievement_percentage', None) is None else str(result.achievement_percentage),
        'qualitative_summary': getattr(result, 'qualitative_summary', None),
        'constraint_notes': getattr(result, 'constraint_notes', None),
        'narrative_context_json': getattr(result, 'narrative_context_json', {}) or {},
        'source_snapshot_json': getattr(result, 'source_snapshot_json', {}) or {},
        'calculated_at': iso_or_none(getattr(result, 'calculated_at', None)),
        'created_at': iso_or_none(getattr(result, 'created_at', None)),
        'updated_at': iso_or_none(getattr(result, 'updated_at', None)),
    }


def serialize_progress_item(item):
    if not item:
        return None
    if isinstance(item, dict):
        return item
    return {
        'id': item.id,
        'uuid': item.uuid,
        'progress_entry_id': item.progress_entry_id,
        'item_order': item.item_order,
        'status': item.status,
        'title': item.title,
        'description': getattr(item, 'description', None),
        'narrative_context_json': getattr(item, 'narrative_context_json', {}) or {},
        'created_at': iso_or_none(getattr(item, 'created_at', None)),
        'updated_at': iso_or_none(getattr(item, 'updated_at', None)),
    }


def serialize_progress_entry(entry):
    if not entry:
        return None
    if isinstance(entry, dict):
        return entry
    return {
        'id': entry.id,
        'uuid': entry.uuid,
        'indicator_version_id': entry.indicator_version_id,
        'reporting_year': getattr(entry, 'reporting_year', None),
        'reporting_period_id': getattr(entry, 'reporting_period_id', None),
        'status': entry.status,
        'progress_percent': None if getattr(entry, 'progress_percent', None) is None else str(entry.progress_percent),
        'qualitative_summary': getattr(entry, 'qualitative_summary', None),
        'constraint_notes': getattr(entry, 'constraint_notes', None),
        'narrative_context_json': getattr(entry, 'narrative_context_json', {}) or {},
        'summary_json': getattr(entry, 'summary_json', {}) or {},
        'items': [serialize_progress_item(item) for item in getattr(entry, 'items', []) or []],
        'created_at': iso_or_none(getattr(entry, 'created_at', None)),
        'updated_at': iso_or_none(getattr(entry, 'updated_at', None)),
    }


def serialize_dataset_definition(dataset):
    if not dataset:
        return None
    if isinstance(dataset, dict):
        return dataset
    return {
        'id': dataset.id,
        'uuid': dataset.uuid,
        'dataset_key': dataset.dataset_key,
        'name': dataset.name,
        'description': getattr(dataset, 'description', None),
        'source_domain': dataset.source_domain,
        'source_type': dataset.source_type,
        'primary_source_ref': getattr(dataset, 'primary_source_ref', None),
        'status': dataset.status,
        'is_active': dataset.is_active,
        'is_year_scoped': getattr(dataset, 'is_year_scoped', None),
        'default_reporting_year_mode': getattr(dataset, 'default_reporting_year_mode', None),
        'owner_scope_type': getattr(dataset, 'owner_scope_type', None),
        'owner_scope_code': getattr(dataset, 'owner_scope_code', None),
        'owner_scope_name': getattr(dataset, 'owner_scope_name', None),
        'owner_scope_path': getattr(dataset, 'owner_scope_path', []) or [],
        'settings_json': getattr(dataset, 'settings_json', {}) or {},
        'tags_json': getattr(dataset, 'tags_json', []) or [],
        'created_at': iso_or_none(getattr(dataset, 'created_at', None)),
        'updated_at': iso_or_none(getattr(dataset, 'updated_at', None)),
    }


def serialize_dataset_version(version):
    if not version:
        return None
    if isinstance(version, dict):
        return version
    return {
        'id': version.id,
        'uuid': version.uuid,
        'dataset_id': version.dataset_id,
        'version_number': version.version_number,
        'status': version.status,
        'is_current_draft': version.is_current_draft,
        'is_current_published': version.is_current_published,
        'source_contract_json': getattr(version, 'source_contract_json', {}) or {},
        'query_spec_json': getattr(version, 'query_spec_json', {}) or {},
        'transform_spec_json': getattr(version, 'transform_spec_json', {}) or {},
        'join_registry_spec_json': getattr(version, 'join_registry_spec_json', []) or [],
        'grain_key': version.grain_key,
        'output_schema_json': getattr(version, 'output_schema_json', []) or [],
        'dimension_definitions_json': getattr(version, 'dimension_definitions_json', []) or [],
        'metric_definitions_json': getattr(version, 'metric_definitions_json', []) or [],
        'default_filters_json': getattr(version, 'default_filters_json', {}) or {},
        'sort_spec_json': getattr(version, 'sort_spec_json', []) or [],
        'freshness_source_type': version.freshness_source_type,
        'freshness_source_ref': getattr(version, 'freshness_source_ref', None),
        'freshness_strategy': version.freshness_strategy,
        'freshness_policy_json': getattr(version, 'freshness_policy_json', {}) or {},
        'publish_notes': getattr(version, 'publish_notes', None),
        'published_at': iso_or_none(getattr(version, 'published_at', None)),
        'created_at': iso_or_none(getattr(version, 'created_at', None)),
        'updated_at': iso_or_none(getattr(version, 'updated_at', None)),
    }


def serialize_dataset_run(run):
    if not run:
        return None
    if isinstance(run, dict):
        return run
    return {
        'id': run.id,
        'uuid': run.uuid,
        'dataset_id': run.dataset_id,
        'dataset_version_id': run.dataset_version_id,
        'run_key': run.run_key,
        'trigger_type': run.trigger_type,
        'trigger_ref': getattr(run, 'trigger_ref', None),
        'requested_reporting_year': getattr(run, 'requested_reporting_year', None),
        'requested_reporting_period_id': getattr(run, 'requested_reporting_period_id', None),
        'requested_filters_json': getattr(run, 'requested_filters_json', {}) or {},
        'status': run.status,
        'started_at': iso_or_none(getattr(run, 'started_at', None)),
        'finished_at': iso_or_none(getattr(run, 'finished_at', None)),
        'duration_ms': getattr(run, 'duration_ms', None),
        'source_watermark': getattr(run, 'source_watermark', None),
        'freshness_status': getattr(run, 'freshness_status', None),
        'source_snapshot_json': getattr(run, 'source_snapshot_json', {}) or {},
        'freshness_evaluated_at': iso_or_none(getattr(run, 'freshness_evaluated_at', None)),
        'result_row_count': getattr(run, 'result_row_count', None),
        'result_schema_json': getattr(run, 'result_schema_json', []) or [],
        'result_preview_json': getattr(run, 'result_preview_json', []) or [],
        'materialization_ref': getattr(run, 'materialization_ref', None),
        'summary_json': getattr(run, 'summary_json', {}) or {},
        'error_code': getattr(run, 'error_code', None),
        'error_message': getattr(run, 'error_message', None),
        'error_detail_json': getattr(run, 'error_detail_json', {}) or {},
        'created_at': iso_or_none(getattr(run, 'created_at', None)),
        'updated_at': iso_or_none(getattr(run, 'updated_at', None)),
    }


def serialize_dataset_workspace_item(item):
    return {
        'dataset': serialize_dataset_definition(item.get('dataset')),
        'draft_version': serialize_dataset_version(item.get('draft_version')),
        'published_version': serialize_dataset_version(item.get('published_version')),
        'latest_run': serialize_dataset_run(item.get('latest_run')),
    }



def parse_int_query_arg(name, default=None):
    raw_value = request.args.get(name, default)
    if raw_value in (None, ''):
        return default
    try:
        return int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Query parameter {name} harus berupa integer.') from error



def serialize_report_workspace_item(item):
    return {
        'report': serialize_report_definition(item.get('report')),
        'draft_version': serialize_report_version(item.get('draft_version')),
        'published_version': serialize_report_version(item.get('published_version')),
        'indicator_mapping_count': item.get('indicator_mapping_count', 0),
    }



def serialize_indicator_workspace_item(item):
    return {
        'indicator': serialize_indicator_definition(item.get('indicator')),
        'draft_version': serialize_indicator_version(item.get('draft_version')),
        'published_version': serialize_indicator_version(item.get('published_version')),
        'latest_result': serialize_indicator_result(item.get('latest_result')),
        'latest_progress_entry': serialize_progress_entry(item.get('latest_progress_entry')),
    }


@api_analytics_bp.route('/datasets', methods=['POST'])
@swag_from(CREATE_DATASET_DOC)
def create_dataset_definition():
    """Membuat dataset analytics beserta draft contract awal.

    Payload create menggabungkan definition dataset dan draft contract agar flow
    `source -> selected fields -> dimension/metric -> report readiness` bisa
    disimpan sekaligus dari UI builder Domain 5.
    """

    data = request.get_json(silent=True) or {}
    try:
        result = AnalyticsDatasetService().create_dataset_bundle(data, actor=current_actor())
        return json_response(
            True,
            'Analytics dataset berhasil dibuat.',
            {
                'dataset': serialize_dataset_definition(result.get('dataset')),
                'draft_version': serialize_dataset_version(result.get('draft_version')),
            },
            status=201,
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics dataset API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics dataset API error: %s', str(error))
        return json_response(False, 'Gagal membuat analytics dataset.', status=500)


@api_analytics_bp.route('/datasets', methods=['GET'])
@swag_from(LIST_DATASETS_DOC)
def list_dataset_definitions():
    try:
        datasets = AnalyticsQueryService().list_datasets()
        return json_response(
            True,
            'Daftar analytics dataset berhasil diambil.',
            {'datasets': [serialize_dataset_workspace_item(item) for item in datasets]},
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('List analytics dataset API error: %s', str(error))
        return json_response(False, 'Gagal mengambil daftar analytics dataset.', status=500)


@api_analytics_bp.route('/datasets/<int:dataset_id>', methods=['GET'])
@swag_from(GET_DATASET_WORKSPACE_DOC)
def get_dataset_workspace(dataset_id):
    try:
        auto_enqueue_stale = request.args.get('auto_enqueue_stale') in {'1', 'true', 'yes'}
        workspace = AnalyticsQueryService().get_dataset_workspace(
            dataset_id,
            auto_enqueue_stale=auto_enqueue_stale,
            actor=current_actor(),
        )
        return json_response(
            True,
            'Detail analytics dataset berhasil diambil.',
            {
                'dataset': serialize_dataset_definition(workspace.get('dataset')),
                'draft_version': serialize_dataset_version(workspace.get('draft_version')),
                'published_version': serialize_dataset_version(workspace.get('published_version')),
                'versions': [serialize_dataset_version(version) for version in workspace.get('versions', [])],
                'runs': [serialize_dataset_run(run) for run in workspace.get('runs', [])],
                'freshness': workspace.get('freshness') or {},
                'auto_refresh': workspace.get('auto_refresh') or {},
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('Get analytics dataset detail API error: %s', str(error))
        return json_response(False, 'Gagal mengambil detail analytics dataset.', status=500)


@api_analytics_bp.route('/datasets/<int:dataset_id>', methods=['PUT'])
@swag_from(UPDATE_DATASET_DOC)
def update_dataset_definition(dataset_id):
    """Memperbarui dataset analytics dan draft contract aktif.

    Route ini dipakai editor dataset supaya perubahan source picker, selected
    fields, metric, dimension, dan notes semi-CMS report tetap terkonsolidasi
    pada satu save action.
    """

    data = request.get_json(silent=True) or {}
    try:
        result = AnalyticsDatasetService().update_dataset_bundle(
            dataset_id=dataset_id,
            data=data,
            actor=current_actor(),
        )
        return json_response(
            True,
            'Analytics dataset berhasil diperbarui.',
            {
                'dataset': serialize_dataset_definition(result.get('dataset')),
                'draft_version': serialize_dataset_version(result.get('draft_version')),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Update analytics dataset API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Update analytics dataset API error: %s', str(error))
        return json_response(False, 'Gagal memperbarui analytics dataset.', status=500)


@api_analytics_bp.route('/datasets/<int:dataset_id>/runs', methods=['GET'])
@swag_from(LIST_DATASET_RUNS_DOC)
def list_dataset_runs(dataset_id):
    try:
        runs = AnalyticsQueryService().list_dataset_runs(dataset_id)
        return json_response(
            True,
            'Daftar analytics dataset run berhasil diambil.',
            {'runs': [serialize_dataset_run(run) for run in runs]},
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('List analytics dataset run API error: %s', str(error))
        return json_response(False, 'Gagal mengambil daftar analytics dataset run.', status=500)


@api_analytics_bp.route('/runs/<int:run_id>', methods=['GET'])
@swag_from(GET_DATASET_RUN_DETAIL_DOC)
def get_dataset_run_detail(run_id):
    try:
        run = AnalyticsQueryService().get_dataset_run_detail(run_id)
        return json_response(
            True,
            'Detail analytics dataset run berhasil diambil.',
            {'run': serialize_dataset_run(run)},
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('Get analytics dataset run detail API error: %s', str(error))
        return json_response(False, 'Gagal mengambil detail analytics dataset run.', status=500)


@api_analytics_bp.route('/datasets/<int:dataset_id>/versions/<int:dataset_version_id>/runs', methods=['POST'])
@swag_from(CREATE_DATASET_RUN_DOC)
def create_dataset_run(dataset_id, dataset_version_id):
    """Mengantrekan dataset run agar materialization berjalan async di worker.

    Endpoint ini menjadi jembatan eksplisit dari source operasional (terutama
    form submissions) menuju materialisasi dataset analytics. Response cepat
    mengembalikan run status `queued`; UI melakukan polling ke endpoint detail run
    sampai status berubah menjadi `running`, `succeeded`, atau `failed`.
    """

    data = request.get_json(silent=True) or {}
    try:
        enqueue_result = AnalyticsDatasetRunService().enqueue_run(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            data=data,
            actor=current_actor(),
        )
        run = enqueue_result['run']
        return json_response(
            True,
            'Analytics dataset run berhasil masuk antrean refresh.',
            {
                'run': serialize_dataset_run(run),
                'dispatch': enqueue_result.get('dispatch') or {},
            },
            status=202,
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics dataset run API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics dataset run API error: %s', str(error))
        return json_response(False, 'Gagal memulai analytics dataset run.', status=500)


@api_analytics_bp.route('/dataset-versions/<int:version_id>/publish', methods=['POST'])
@swag_from(PUBLISH_DATASET_VERSION_DOC)
def publish_dataset_version(version_id):
    """Mempublish dataset contract agar siap dipakai dataset run dan report dinamis."""

    request.get_json(silent=True) or {}
    try:
        version = AnalyticsDatasetService().publish_dataset_version(version_id, actor=current_actor())
        return json_response(
            True,
            'Analytics dataset version berhasil dipublish.',
            {'dataset_version': serialize_dataset_version(version)},
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Publish analytics dataset version API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Publish analytics dataset version API error: %s', str(error))
        return json_response(False, 'Gagal publish analytics dataset version.', status=500)


@api_analytics_bp.route('/reports', methods=['GET'])
@swag_from(LIST_REPORTS_DOC)
def list_report_definitions():
    try:
        reports = AnalyticsQueryService().list_reports()
        return json_response(
            True,
            'Daftar analytics report berhasil diambil.',
            {'reports': [serialize_report_workspace_item(item) for item in reports]},
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('List analytics report API error: %s', str(error))
        return json_response(False, 'Gagal mengambil daftar analytics report.', status=500)


@api_analytics_bp.route('/reports/<int:report_definition_id>', methods=['GET'])
@swag_from(GET_REPORT_WORKSPACE_DOC)
def get_report_workspace(report_definition_id):
    try:
        workspace = AnalyticsQueryService().get_report_workspace(report_definition_id)
        return json_response(
            True,
            'Detail analytics report berhasil diambil.',
            {
                'report': serialize_report_definition(workspace.get('report')),
                'draft_version': serialize_report_version(workspace.get('draft_version')),
                'published_version': serialize_report_version(workspace.get('published_version')),
                'versions': [serialize_report_version(version) for version in workspace.get('versions', [])],
                'indicator_mappings': [
                    {
                        'mapping': serialize_report_mapping(item.get('mapping')),
                        'indicator_version': serialize_indicator_version(item.get('indicator_version')),
                        'indicator_definition': serialize_indicator_definition(item.get('indicator_definition')),
                    }
                    for item in workspace.get('indicator_mappings', [])
                ],
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('Get analytics report detail API error: %s', str(error))
        return json_response(False, 'Gagal mengambil detail analytics report.', status=500)


@api_analytics_bp.route('/indicators', methods=['GET'])
@swag_from(LIST_INDICATORS_DOC)
def list_indicator_definitions():
    try:
        indicators = AnalyticsQueryService().list_indicators()
        return json_response(
            True,
            'Daftar analytics indicator berhasil diambil.',
            {'indicators': [serialize_indicator_workspace_item(item) for item in indicators]},
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('List analytics indicator API error: %s', str(error))
        return json_response(False, 'Gagal mengambil daftar analytics indicator.', status=500)


@api_analytics_bp.route('/indicators/<int:indicator_definition_id>', methods=['GET'])
@swag_from(GET_INDICATOR_WORKSPACE_DOC)
def get_indicator_workspace(indicator_definition_id):
    try:
        workspace = AnalyticsQueryService().get_indicator_workspace(indicator_definition_id)
        return json_response(
            True,
            'Detail analytics indicator berhasil diambil.',
            {
                'indicator': serialize_indicator_definition(workspace.get('indicator')),
                'draft_version': serialize_indicator_version(workspace.get('draft_version')),
                'published_version': serialize_indicator_version(workspace.get('published_version')),
                'versions': [serialize_indicator_version(version) for version in workspace.get('versions', [])],
                'results': [serialize_indicator_result(result) for result in workspace.get('results', [])],
                'progress_entries': [serialize_progress_entry(entry) for entry in workspace.get('progress_entries', [])],
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('Get analytics indicator detail API error: %s', str(error))
        return json_response(False, 'Gagal mengambil detail analytics indicator.', status=500)


@api_analytics_bp.route('/indicator-results', methods=['GET'])
@swag_from(LIST_INDICATOR_RESULTS_DOC)
def list_indicator_results():
    try:
        indicator_version_id = parse_int_query_arg('indicator_version_id')
        reporting_year = parse_int_query_arg('reporting_year')
        reporting_period_id = parse_int_query_arg('reporting_period_id')
        limit = parse_int_query_arg('limit', 50)
        results = AnalyticsQueryService().list_indicator_results(
            indicator_version_id=indicator_version_id,
            reporting_year=reporting_year,
            reporting_period_id=reporting_period_id,
            limit=limit,
        )
        return json_response(
            True,
            'Daftar analytics indicator result berhasil diambil.',
            {'results': [serialize_indicator_result(result) for result in results]},
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('List analytics indicator result API error: %s', str(error))
        return json_response(False, 'Gagal mengambil daftar analytics indicator result.', status=500)


@api_analytics_bp.route('/reports', methods=['POST'])
@swag_from(CREATE_REPORT_DOC)
def create_report_definition():
    """Membuat report analytics sekaligus draft builder semi-CMS.

    Payload dapat memakai bentuk flat atau nested:
    - report: metadata report + dataset_id
    - draft_version: dataset_version_id, blocks, filter_schema, layout,
      period_preset_config, quick_presets, supported_period_modes,
      meta_description, narrative_*.
    """
    data = request.get_json(silent=True) or {}
    try:
        result = AnalyticsReportService().create_report_bundle(data, actor=current_actor())
        return json_response(
            True,
            'Analytics report berhasil dibuat.',
            {
                'report': serialize_report_definition(result.get('report')),
                'draft_version': serialize_report_version(result.get('draft_version')),
            },
            status=201,
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics report API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics report API error: %s', str(error))
        return json_response(False, 'Gagal membuat analytics report.', status=500)


@api_analytics_bp.route('/reports/<int:report_definition_id>', methods=['PUT'])
@swag_from(UPDATE_REPORT_DOC)
def update_report_definition(report_definition_id):
    """Memperbarui report analytics dan draft builder aktif."""
    data = request.get_json(silent=True) or {}
    try:
        result = AnalyticsReportService().update_report_bundle(
            report_definition_id,
            data,
            actor=current_actor(),
        )
        return json_response(
            True,
            'Analytics report berhasil diperbarui.',
            {
                'report': serialize_report_definition(result.get('report')),
                'draft_version': serialize_report_version(result.get('draft_version')),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Update analytics report API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Update analytics report API error: %s', str(error))
        return json_response(False, 'Gagal memperbarui analytics report.', status=500)


@api_analytics_bp.route('/reports/<int:report_definition_id>/versions', methods=['POST'])
@swag_from(CREATE_REPORT_VERSION_DOC)
def create_report_version(report_definition_id):
    data = request.get_json(silent=True) or {}
    try:
        version = AnalyticsReportService().create_report_version(
            report_definition_id=report_definition_id,
            data=data,
            actor=current_actor(),
        )
        return json_response(True, 'Analytics report version berhasil dibuat.', {'report_version': serialize_report_version(version)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics report version API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics report version API error: %s', str(error))
        return json_response(False, 'Gagal membuat analytics report version.', status=500)


@api_analytics_bp.route('/report-versions/<int:version_id>/publish', methods=['POST'])
@swag_from(PUBLISH_REPORT_VERSION_DOC)
def publish_report_version(version_id):
    request.get_json(silent=True) or {}
    try:
        version = AnalyticsReportService().publish_report_version(version_id, actor=current_actor())
        return json_response(True, 'Analytics report version berhasil dipublish.', {'report_version': serialize_report_version(version)})
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Publish analytics report version API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Publish analytics report version API error: %s', str(error))
        return json_response(False, 'Gagal publish analytics report version.', status=500)


@api_analytics_bp.route('/indicators', methods=['POST'])
@swag_from(CREATE_INDICATOR_DOC)
def create_indicator_definition():
    data = request.get_json(silent=True) or {}
    try:
        indicator = AnalyticsIndicatorService().create_indicator_definition(data, actor=current_actor())
        return json_response(True, 'Analytics indicator berhasil dibuat.', {'indicator': serialize_indicator_definition(indicator)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics indicator API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics indicator API error: %s', str(error))
        return json_response(False, 'Gagal membuat analytics indicator.', status=500)


@api_analytics_bp.route('/indicators/<int:indicator_definition_id>/versions', methods=['POST'])
@swag_from(CREATE_INDICATOR_VERSION_DOC)
def create_indicator_version(indicator_definition_id):
    data = request.get_json(silent=True) or {}
    try:
        version = AnalyticsIndicatorService().create_indicator_version(
            indicator_definition_id=indicator_definition_id,
            data=data,
            actor=current_actor(),
        )
        return json_response(True, 'Analytics indicator version berhasil dibuat.', {'indicator_version': serialize_indicator_version(version)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics indicator version API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics indicator version API error: %s', str(error))
        return json_response(False, 'Gagal membuat analytics indicator version.', status=500)


@api_analytics_bp.route('/indicator-versions/<int:version_id>/publish', methods=['POST'])
@swag_from(PUBLISH_INDICATOR_VERSION_DOC)
def publish_indicator_version(version_id):
    request.get_json(silent=True) or {}
    try:
        version = AnalyticsIndicatorService().publish_indicator_version(version_id, actor=current_actor())
        return json_response(True, 'Analytics indicator version berhasil dipublish.', {'indicator_version': serialize_indicator_version(version)})
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Publish analytics indicator version API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Publish analytics indicator version API error: %s', str(error))
        return json_response(False, 'Gagal publish analytics indicator version.', status=500)


@api_analytics_bp.route('/report-versions/<int:report_version_id>/indicators', methods=['POST'])
@swag_from(ATTACH_INDICATOR_TO_REPORT_DOC)
def attach_indicator_to_report_version(report_version_id):
    data = request.get_json(silent=True) or {}
    try:
        mapping = AnalyticsIndicatorService().attach_indicator_to_report_version(
            report_version_id=report_version_id,
            indicator_version_id=data.get('indicator_version_id'),
            data=data,
            actor=current_actor(),
        )
        return json_response(True, 'Indicator berhasil di-attach ke report version.', {'mapping': serialize_report_mapping(mapping)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Attach analytics indicator API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Attach analytics indicator API error: %s', str(error))
        return json_response(False, 'Gagal attach indicator ke report version.', status=500)


@api_analytics_bp.route('/indicator-results', methods=['POST'])
@swag_from(RECORD_INDICATOR_RESULT_DOC)
def record_indicator_result():
    data = request.get_json(silent=True) or {}
    try:
        result = AnalyticsIndicatorResultService().record_result(data, actor=current_actor())
        return json_response(True, 'Analytics indicator result berhasil disimpan.', {'result': serialize_indicator_result(result)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Record analytics indicator result API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Record analytics indicator result API error: %s', str(error))
        return json_response(False, 'Gagal menyimpan analytics indicator result.', status=500)


@api_analytics_bp.route('/indicator-progress-entries', methods=['POST'])
@swag_from(RECORD_PROGRESS_ENTRY_DOC)
def record_progress_entry():
    data = request.get_json(silent=True) or {}
    try:
        progress_entry = AnalyticsIndicatorResultService().record_progress_entry(data, actor=current_actor())
        return json_response(True, 'Analytics indicator progress entry berhasil disimpan.', {'progress_entry': serialize_progress_entry(progress_entry)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Record analytics progress entry API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Record analytics progress entry API error: %s', str(error))
        return json_response(False, 'Gagal menyimpan analytics progress entry.', status=500)


@api_analytics_bp.route('/indicator-progress-entries/<int:progress_entry_id>/sync-result', methods=['POST'])
@swag_from(SYNC_RESULT_FROM_PROGRESS_DOC)
def sync_result_from_progress(progress_entry_id):
    request.get_json(silent=True) or {}
    try:
        result = AnalyticsIndicatorResultService().sync_result_from_progress(progress_entry_id, actor=current_actor())
        return json_response(True, 'Analytics indicator result berhasil disinkronkan dari progress.', {'result': serialize_indicator_result(result)})
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Sync analytics result from progress API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Sync analytics result from progress API error: %s', str(error))
        return json_response(False, 'Gagal sinkronisasi analytics indicator result dari progress.', status=500)
