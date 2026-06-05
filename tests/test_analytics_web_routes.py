from pathlib import Path

from app import create_app



def test_analytics_workspace_page_smoke_returns_ui_shell_and_assets():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/analytics')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Workspace Analytics Domain 5' in html
    assert 'id="analyticsWorkspaceSummaryCards"' in html
    assert 'id="analyticsReportsGrid"' in html
    assert 'id="analyticsIndicatorsGrid"' in html
    assert 'id="analyticsResultsTable"' in html
    assert 'id="analyticsDatasetRunsPanel"' in html
    assert 'id="analyticsDatasetRunsList"' in html
    assert 'id="analyticsDatasetDetailPanel"' in html
    assert 'id="analyticsReportDetailPanel"' in html
    assert 'id="analyticsIndicatorDetailPanel"' in html
    assert 'id="indicatorDetailTabDefinition"' in html
    assert 'id="indicatorDetailTabFormula"' in html
    assert 'id="indicatorDetailTabTarget"' in html
    assert 'id="indicatorDetailTabNarrative"' in html
    assert 'id="indicatorDetailTabProgressHistory"' in html
    assert 'id="indicatorDetailTabResultHistory"' in html
    assert 'id="indicatorDetailTabContentDefinition"' in html
    assert 'id="indicatorDetailTabContentFormula"' in html
    assert 'id="indicatorDetailTabContentTarget"' in html
    assert 'id="indicatorDetailTabContentNarrative"' in html
    assert 'id="indicatorDetailTabContentProgressHistory"' in html
    assert 'id="indicatorDetailTabContentResultHistory"' in html
    assert 'libs/gridjs/dist/gridjs.umd.js' in html
    assert 'libs/apexcharts/dist/apexcharts.min.js' in html
    assert 'js/pages/analytics-workspace.js' in html
    assert 'analyticsReportsUrl' in html
    assert 'analyticsIndicatorsUrl' in html
    assert 'analyticsResultsUrl' in html
    assert 'analyticsDatasetsUrl' in html
    assert 'analyticsDatasetDetailUrlTemplate' in html
    assert 'analyticsDatasetRunsUrlTemplate' in html
    assert 'analyticsReportDetailUrlTemplate' in html
    assert 'analyticsIndicatorDetailUrlTemplate' in html



def test_analytics_workspace_static_js_is_served():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/static/js/pages/analytics-workspace.js')

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'window.analyticsWorkspaceConfig' in body
    assert 'analyticsDatasetDetailUrlTemplate' in body
    assert 'analyticsIndicatorDetailUrlTemplate' in body
    assert 'Detail Dataset' in body
    assert 'Pilih salah satu dataset untuk melihat contract dan preview hasil run.' in body
    assert 'Gagal memuat dataset runs.' in body



def test_analytics_workspace_source_js_contains_expected_fetch_contract():
    js_path = Path('app/src/js/pages/analytics-workspace.js')
    content = js_path.read_text()

    assert 'window.analyticsWorkspaceConfig' in content
    assert 'analyticsReportsUrl' in content
    assert 'analyticsIndicatorsUrl' in content
    assert 'analyticsResultsUrl' in content
    assert 'analyticsDatasetsUrl' in content
    assert 'analyticsDatasetDetailUrlTemplate' in content
    assert 'analyticsDatasetRunsUrlTemplate' in content
    assert 'analyticsReportDetailUrlTemplate' in content
    assert 'analyticsIndicatorDetailUrlTemplate' in content
    assert 'gridjs.Grid' in content
    assert 'fetchJson' in content
    assert 'renderDatasetRunsPanel' in content
    assert 'renderDatasetDetail' in content
    assert 'loadDatasetDetail' in content
    assert 'loadDatasets' in content
    assert 'renderDatasetSummaryCharts' in content
    assert 'wireQuickFlowActions' in content
    assert 'ApexCharts' in content
    assert 'data-flow-report-id' in content
    assert 'Sedang dibaca' in content
    assert 'renderIndicatorDefinitionTab' in content
    assert 'renderIndicatorFormulaTab' in content
    assert 'renderIndicatorTargetTab' in content
    assert 'renderIndicatorNarrativeTab' in content
    assert 'renderIndicatorProgressHistoryTab' in content
    assert 'renderIndicatorResultHistoryTab' in content
    assert 'setActiveIndicatorTab' in content
