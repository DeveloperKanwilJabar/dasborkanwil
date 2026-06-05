from flask import Blueprint, render_template, url_for


analytics_web_bp = Blueprint('analytics_web', __name__)


@analytics_web_bp.route('/analytics', methods=['GET'])
def analytics_workspace():
    workspace_config = {
        'analyticsReportsUrl': url_for('api_analytics_v1.list_report_definitions'),
        'analyticsIndicatorsUrl': url_for('api_analytics_v1.list_indicator_definitions'),
        'analyticsResultsUrl': url_for('api_analytics_v1.list_indicator_results'),
        'analyticsDatasetsUrl': url_for('api_analytics_v1.list_dataset_definitions'),
        'analyticsDatasetDetailUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__',
        'analyticsDatasetRunsUrlTemplate': '/api/v1/analytics/datasets/__DATASET_ID__/runs',
        'analyticsReportDetailUrlTemplate': '/api/v1/analytics/reports/__REPORT_ID__',
        'analyticsIndicatorDetailUrlTemplate': '/api/v1/analytics/indicators/__INDICATOR_ID__',
    }
    return render_template(
        'pages/analytics/workspace.html',
        workspace_config=workspace_config,
    )
