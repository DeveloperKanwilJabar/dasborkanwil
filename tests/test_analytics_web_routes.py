from pathlib import Path
from types import SimpleNamespace

from app import create_app


def _make_registry(registry_id=1, name='Registry Wilayah'):
    return SimpleNamespace(
        id=registry_id,
        name=name,
        description='Registry untuk kebutuhan analytics wilayah.',
        registry_slug='wilayah-administratif',
        registry_code='WILAYAH-ADM',
        registry_type='geo',
        category_key='wilayah',
        source_mode='import_file',
        data_shape='hierarchical_geo',
        status='published',
    )


def _make_registry_version(version_number=3):
    return SimpleNamespace(
        id=11,
        version_number=version_number,
        schema_json={'fields': [{'key': 'record_code', 'label': 'Kode'}]},
        mapping_spec={'materialization_contract': 'generic_v1'},
        source_snapshot={'source_name': 'browser_manual_setup'},
    )


def _make_dataset(dataset_id=7, primary_source_ref='WILAYAH-ADM'):
    return {
        'dataset': SimpleNamespace(
            id=dataset_id,
            dataset_key='dataset-wilayah',
            name='Dataset Wilayah',
            description='Dataset analytics wilayah',
            source_domain='data_registry',
            source_type='published_registry_dimension',
            primary_source_ref=primary_source_ref,
            settings_json={},
            tags_json=[],
        ),
        'draft_version': None,
        'published_version': SimpleNamespace(
            id=21,
            version_number=2,
            source_contract_json={'registry_code': 'WILAYAH-ADM'},
            join_registry_spec_json={},
            query_spec_json={},
            transform_spec_json={},
        ),
        'latest_run': None,
    }



def test_analytics_index_page_shows_published_registry_table(monkeypatch):
    app = create_app('testing')

    registry = _make_registry()
    published_version = _make_registry_version()

    class StubRegistryRepo:
        def get_all(self):
            return [registry]

    class StubVersionRepo:
        def get_draft_version(self, registry_id):
            return None

        def get_published_version(self, registry_id):
            return published_version

    class StubDataRegistryService:
        def __init__(self):
            self.repository = StubRegistryRepo()

    class StubDataRegistryVersionService:
        def __init__(self):
            self.repository = StubVersionRepo()

    class StubAnalyticsQueryService:
        def list_datasets(self):
            return [_make_dataset()]

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Analytics Domain 5' in html
    assert 'Daftar Data Registry yang Sudah Publish' in html
    assert 'Buka Detail Report' in html
    assert 'Metadata' in html
    assert 'Workspace Registry' in html
    assert 'Registry Wilayah' in html
    assert 'Published v3' in html
    assert '1 dataset' in html



def test_analytics_detail_report_page_renders_humanized_focus_layout(monkeypatch):
    app = create_app('testing')

    registry = _make_registry()
    published_version = _make_registry_version()
    workspace_payload = {
        'registry': registry,
        'draft_version': None,
        'published_version': published_version,
        'manual_entry_version': published_version,
        'record_count': 12,
    }

    class StubDataRegistryService:
        def get_registry_workspace(self, registry_id, record_limit=8):
            return workspace_payload

    class StubAnalyticsQueryService:
        def list_datasets(self):
            return [_make_dataset()]

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/1')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Detail Report Analytics' in html
    assert 'Metadata Registry' in html
    assert 'Ke Chart' in html
    assert 'Ke Peta' in html
    assert 'id="analyticsDetailDatasetSelect"' in html
    assert 'id="analyticsDatasetMetricCards"' in html
    assert 'id="analyticsDatasetChart"' in html
    assert 'id="analyticsDatasetMap"' in html
    assert 'id="analyticsDatasetRunsList"' in html
    assert 'id="analyticsDatasetRunButton"' in html
    assert 'id="analyticsDatasetExecutionStatus"' in html
    assert 'Jembatan Submission ke Analytics' in html
    assert 'libs/plotly.js-dist-min/plotly.min.js' in html
    assert 'libs/leaflet/dist/leaflet.js' in html
    assert 'js/pages/analytics-workspace.js' in html
    assert 'analyticsDatasetsUrl' in html
    assert 'analyticsDatasetDetailUrlTemplate' in html
    assert 'analyticsDatasetRunsUrlTemplate' in html
    assert '7 Hari Terakhir' in html
    assert 'Triwulan Ini' in html
    assert 'Semester Ini' in html
    assert 'Tahun Ini' in html



def test_analytics_metadata_page_separates_registry_metadata(monkeypatch):
    app = create_app('testing')

    registry = _make_registry()
    published_version = _make_registry_version()
    workspace_payload = {
        'registry': registry,
        'draft_version': None,
        'published_version': published_version,
        'manual_entry_version': published_version,
        'record_count': 99,
    }

    class StubDataRegistryService:
        def get_registry_workspace(self, registry_id, record_limit=8):
            return workspace_payload

    class StubAnalyticsQueryService:
        def list_datasets(self):
            return [_make_dataset()]

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/1/metadata')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Metadata Analytics Registry' in html
    assert 'Schema JSON Published' in html
    assert 'Mapping &amp; Source Snapshot' in html or 'Mapping & Source Snapshot' in html
    assert 'Kembali ke Detail Report' in html
    assert 'Dataset analytics terkait' in html
    assert 'record_count' not in html



def test_analytics_workspace_static_js_is_served():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/static/js/pages/analytics-workspace.js')

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'window.analyticsWorkspaceConfig' in body
    assert 'analyticsDetailDatasetSelect' in body
    assert 'analyticsDatasetRunsList' in body
    assert 'analyticsDatasetMap' in body
    assert 'analyticsDatasetRunButton' in body
    assert 'analyticsDatasetExecutionStatus' in body
    assert 'analyticsDatasetExecuteUrlTemplate' in body
    assert 'Gagal memuat dataset runs.' in body



def test_analytics_workspace_source_js_contains_expected_fetch_and_filter_contract():
    js_path = Path('app/src/js/pages/analytics-workspace.js')
    content = js_path.read_text()

    assert 'window.analyticsWorkspaceConfig' in content
    assert 'analyticsDatasetsUrl' in content
    assert 'analyticsDatasetDetailUrlTemplate' in content
    assert 'analyticsDatasetRunsUrlTemplate' in content
    assert 'fetchJson' in content
    assert 'datasetMatchesRegistry' in content
    assert 'applyDatasetFilters' in content
    assert 'aggregateRows' in content
    assert 'renderMetricCards' in content
    assert 'renderChart' in content
    assert 'renderMap' in content
    assert 'loadDatasets' in content
    assert 'loadDatasetDetail' in content
    assert 'loadDatasetRuns' in content
    assert 'getCalendarPresetRange' in content
    assert 'analyticsDatasetMetricCards' in content
    assert 'analyticsDatasetChart' in content
    assert 'analyticsDatasetMap' in content
    assert 'current_quarter' in content
    assert 'current_semester' in content
    assert 'current_year' in content
    assert 'full_range' in content
