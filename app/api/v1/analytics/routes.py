from flask import Blueprint, current_app, request
from flask_login import current_user

from app.core.extensions import db
from app.core.utils import json_response
from app.modules.analytics.services import (
    AnalyticsDatasetRunService,
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


@api_analytics_bp.route('/datasets', methods=['GET'])
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
def get_dataset_workspace(dataset_id):
    try:
        workspace = AnalyticsQueryService().get_dataset_workspace(dataset_id)
        return json_response(
            True,
            'Detail analytics dataset berhasil diambil.',
            {
                'dataset': serialize_dataset_definition(workspace.get('dataset')),
                'draft_version': serialize_dataset_version(workspace.get('draft_version')),
                'published_version': serialize_dataset_version(workspace.get('published_version')),
                'versions': [serialize_dataset_version(version) for version in workspace.get('versions', [])],
                'runs': [serialize_dataset_run(run) for run in workspace.get('runs', [])],
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error('Get analytics dataset detail API error: %s', str(error))
        return json_response(False, 'Gagal mengambil detail analytics dataset.', status=500)


@api_analytics_bp.route('/datasets/<int:dataset_id>/runs', methods=['GET'])
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
def create_dataset_run(dataset_id, dataset_version_id):
    data = request.get_json(silent=True) or {}
    try:
        run = AnalyticsDatasetRunService().start_run(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            data=data,
            actor=current_actor(),
        )
        return json_response(
            True,
            'Analytics dataset run berhasil dimulai.',
            {'run': serialize_dataset_run(run)},
            status=201,
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


@api_analytics_bp.route('/reports', methods=['GET'])
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
def create_report_definition():
    data = request.get_json(silent=True) or {}
    try:
        report = AnalyticsReportService().create_report_definition(data, actor=current_actor())
        return json_response(True, 'Analytics report berhasil dibuat.', {'report': serialize_report_definition(report)}, status=201)
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning('Create analytics report API authorization error: %s', str(error))
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error('Create analytics report API error: %s', str(error))
        return json_response(False, 'Gagal membuat analytics report.', status=500)


@api_analytics_bp.route('/reports/<int:report_definition_id>/versions', methods=['POST'])
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
