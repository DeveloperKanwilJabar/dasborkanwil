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
    assert 'id="analyticsResultsFilterReportingYear"' in html
    assert 'id="analyticsResultsFilterStatus"' in html
    assert 'id="analyticsDatasetFilterReportingYear"' in html
    assert 'id="analyticsDatasetFilterStatus"' in html
    assert 'id="analyticsDatasetFilterJenis"' in html
    assert 'id="analyticsDatasetFilterDateStart"' in html
    assert 'id="analyticsDatasetFilterDateEnd"' in html
    assert 'id="analyticsDatasetMetricPeriodMode"' in html
    assert '<option value="daily">Harian</option>' in html
    assert '<option value="weekly">Mingguan</option>' in html
    assert '<option value="monthly">Bulanan</option>' in html
    assert '<option value="four_monthly">Caturwulan</option>' in html
    assert 'data-quick-range="last_7_days"' in html
    assert 'data-quick-range="current_week"' in html
    assert 'data-quick-range="current_month"' in html
    assert 'data-quick-range="current_quarter"' in html
    assert 'data-quick-range="current_semester"' in html
    assert 'data-quick-range="current_year"' in html
    assert 'id="analyticsDatasetInsightPanel"' in html
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
    assert 'libs/plotly.js-dist-min/plotly.min.js' in html
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
    assert 'analyticsDatasetFilterDateStart' in body
    assert 'analyticsDatasetFilterDateEnd' in body
    assert 'current_semester' in body
    assert 'current_week' in body
    assert 'current_year' in body
    assert 'last_7_days' in body
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
    assert 'renderDatasetInsights' in content
    assert 'applyDatasetFilters' in content
    assert 'populateDatasetFilterControls' in content
    assert 'handleResultRowSelection' in content
    assert 'analyticsResultsFilterReportingYear' in content
    assert 'analyticsDatasetFilterDateStart' in content
    assert 'analyticsDatasetFilterDateEnd' in content
    assert 'analyticsDatasetMetricPeriodMode' in content
    assert 'wireResultTableActions' in content
    assert 'wireQuickFlowActions' in content
    assert 'Plotly' in content
    assert 'renderPlotlyChart' in content
    assert 'resolveRowDate' in content
    assert 'resolvePresetDateRange' in content
    assert 'applyQuickDatePreset' in content
    assert 'Caturwulan' in content
    assert 'Triwulan' in content
    assert 'Semester' in content
    assert 'current_month' in content
    assert 'current_week' in content
    assert 'current_quarter' in content
    assert 'current_semester' in content
    assert 'current_year' in content
    assert 'resolvePresetAnchorDate' in content
    assert 'clampDateToRange' in content
    assert 'selectedIndicatorVersionId = normalizedIndicatorVersionId' in content
    assert 'selectedIndicatorVersionId = options.selectedIndicatorVersionId || activeVersion.id || null' in content
    assert 'colspan="8" class="text-danger"' in content
    assert 'data-flow-report-id' in content
    assert 'Sedang dibaca' in content
    assert 'renderIndicatorDefinitionTab' in content
    assert 'renderIndicatorFormulaTab' in content
    assert 'renderIndicatorTargetTab' in content
    assert 'renderIndicatorNarrativeTab' in content
    assert 'renderIndicatorProgressHistoryTab' in content
    assert 'renderIndicatorResultHistoryTab' in content
    assert 'setActiveIndicatorTab' in content
    assert 'bindAnalyticsFilterControls();' in content
