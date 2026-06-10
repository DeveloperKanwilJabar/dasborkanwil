from pathlib import Path
from types import SimpleNamespace

from app import create_app


def _make_registry(registry_id=1, name='Registry Wilayah'):
    return SimpleNamespace(
        id=registry_id,
        uuid=f'registry-{registry_id}-uuid',
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


def _make_dataset_run(run_id=31, status='succeeded'):
    return SimpleNamespace(
        id=run_id,
        status=status,
        result_row_count=42,
        updated_at='2026-06-09T10:00:00+00:00',
        requested_reporting_year=2026,
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
            status='published',
            is_current_draft=False,
            is_current_published=True,
            source_contract_json={'registry_code': 'WILAYAH-ADM'},
            join_registry_spec_json={},
            query_spec_json={},
            transform_spec_json={},
            output_schema_json=[
                {'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'},
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
                {'key': 'latitude', 'label': 'Latitude', 'type': 'number'},
                {'key': 'longitude', 'label': 'Longitude', 'type': 'number'},
            ],
            dimension_definitions_json=[
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
            ],
            metric_definitions_json=[
                {'key': 'capaian_total', 'label': 'Capaian Total', 'type': 'integer'},
                {'key': 'achievement_pct', 'label': 'Achievement %', 'type': 'number'},
            ],
        ),
        'latest_run': _make_dataset_run(),
    }


def _make_dataset_workspace_payload(dataset_id=7):
    dataset_item = _make_dataset(dataset_id=dataset_id)
    published_version = dataset_item['published_version']
    workspace_version = SimpleNamespace(
        id=published_version.id,
        version_number=published_version.version_number,
        status='published',
        is_current_draft=False,
        is_current_published=True,
    )
    return {
        'dataset': dataset_item['dataset'],
        'draft_version': None,
        'published_version': published_version,
        'versions': [workspace_version],
        'runs': [_make_dataset_run()],
    }


def _make_report_item(report_id=21, dataset_id=7):
    return {
        'report': SimpleNamespace(
            id=report_id,
            dataset_id=dataset_id,
            report_key='pk-kanwil',
            name='PK Kanwil',
            category_key='pk',
            settings_json={'linked_dataset_name': 'Dataset Wilayah', 'linked_dataset_key': 'dataset-wilayah'},
        ),
        'draft_version': SimpleNamespace(
            id=31,
            version_number=1,
            dataset_version_id=21,
            title='PK Kanwil 2026',
            meta_description='Narasi laporan tahun aktif.',
            structure_json={
                'period_preset_config': {
                    'default_mode': 'quarterly',
                    'supported_period_modes': ['quarterly', 'yearly'],
                    'quick_presets': ['current_quarter', 'current_year'],
                },
                'dataset_contract': {
                    'dataset_id': dataset_id,
                    'dataset_version_id': 21,
                    'dataset_version_number': 2,
                    'grain_key': 'per_scope_per_year',
                    'run_binding': {
                        'dataset_id': dataset_id,
                        'dataset_key': 'dataset-wilayah',
                        'dataset_version_id': 21,
                        'dataset_version_number': 2,
                        'report_title': 'PK Kanwil',
                        'report_category_key': 'pk',
                        'selection_mode': 'latest_succeeded_run',
                    },
                    'curated_fields': [
                        {'key': 'tanggal', 'label': 'Tanggal', 'role': 'date', 'type': 'date'},
                        {'key': 'nama_indikator', 'label': 'Nama Indikator', 'role': 'dimension', 'type': 'string'},
                        {'key': 'capaian_total', 'label': 'Capaian Total', 'role': 'metric', 'type': 'integer'},
                        {'key': 'achievement_pct', 'label': 'Achievement %', 'role': 'metric', 'type': 'number'},
                        {'key': 'latitude', 'label': 'Latitude', 'role': 'geo_latitude', 'type': 'number'},
                        {'key': 'longitude', 'label': 'Longitude', 'role': 'geo_longitude', 'type': 'number'},
                    ],
                },
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Ringkasan KPI', 'config': {'metric_keys': ['capaian_total', 'achievement_pct']}},
                    {'type': 'plotly_timeseries', 'title': 'Tren Kinerja', 'config': {'x_key': 'tanggal', 'series': [{'key': 'capaian_total', 'label': 'Capaian Total'}]}},
                    {'type': 'detail_table', 'title': 'Tabel Detail Kinerja', 'config': {'column_keys': ['tanggal', 'nama_indikator', 'capaian_total', 'achievement_pct']}},
                    {'type': 'geo_map', 'title': 'Sebaran Wilayah', 'config': {'latitude_field': 'latitude', 'longitude_field': 'longitude', 'label_field': 'nama_indikator'}},
                    {'type': 'narrative', 'title': 'Narasi Eksekutif', 'config': {'focus_field_keys': ['achievement_pct', 'capaian_total']}},
                ],
            },
            narrative_guidance_json={'summary_prompt': 'Ringkas capaian.'},
        ),
        'published_version': None,
        'indicator_mapping_count': 0,
    }


def _make_report_workspace_payload(report_id=21, dataset_id=7):
    report_item = _make_report_item(report_id=report_id, dataset_id=dataset_id)
    return {
        'report': report_item['report'],
        'draft_version': report_item['draft_version'],
        'published_version': report_item['published_version'],
        'versions': [report_item['draft_version']],
        'indicator_mappings': [],
    }


class StubRegistryRepo:
    def __init__(self, registry):
        self._registry = registry

    def get_all(self):
        return [self._registry]


class StubVersionRepo:
    def __init__(self, published_version):
        self._published_version = published_version

    def get_draft_version(self, registry_id):
        return None

    def get_published_version(self, registry_id):
        return self._published_version


class StubDataRegistryService:
    def __init__(self, registry=None, workspace_payload=None):
        self._registry = registry or _make_registry()
        self._workspace_payload = workspace_payload or {
            'registry': self._registry,
            'draft_version': None,
            'published_version': _make_registry_version(),
            'manual_entry_version': _make_registry_version(),
            'record_count': 99,
        }
        self.repository = StubRegistryRepo(self._registry)

    def get_registry_workspace(self, registry_id, record_limit=8):
        return self._workspace_payload


class StubDataRegistryVersionService:
    def __init__(self, published_version=None):
        self.repository = StubVersionRepo(published_version or _make_registry_version())


class StubAnalyticsQueryService:
    def __init__(self, dataset_item=None, workspace_payload=None, report_item=None, report_workspace_payload=None):
        self._dataset_item = dataset_item or _make_dataset()
        self._workspace_payload = workspace_payload or _make_dataset_workspace_payload(self._dataset_item['dataset'].id)
        self._report_item = report_item or _make_report_item(dataset_id=self._dataset_item['dataset'].id)
        self._report_workspace_payload = report_workspace_payload or _make_report_workspace_payload(dataset_id=self._dataset_item['dataset'].id)

    def list_datasets(self):
        return [self._dataset_item]

    def get_dataset_workspace(self, dataset_id):
        return self._workspace_payload

    def list_reports(self):
        return [self._report_item]

    def get_report_workspace(self, report_definition_id):
        return self._report_workspace_payload


def test_analytics_index_page_shows_dataset_catalog(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Analytics Datasets' in html
    assert 'Katalog Dataset Analytics' in html
    assert 'Buat Dataset' in html
    assert 'Linkage Registry' in html
    assert 'Dataset Wilayah' in html
    assert 'Viewer' in html
    assert 'Workspace' in html
    assert 'Builder Report' in html
    assert 'Edit' in html
    assert 'Registry Wilayah' in html


def test_analytics_registry_linkage_page_shows_registry_browser(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/registries')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Linkage Registry Analytics' in html
    assert 'Daftar Registry Publish & Linkage Dataset' in html
    assert 'Lihat Dataset Terkait' in html
    assert 'Metadata' in html
    assert 'Workspace Registry' in html
    assert '1 dataset' in html


def test_analytics_registry_datasets_page_shows_dataset_actions(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/registries/1/datasets')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Dataset Terkait Registry' in html
    assert 'Daftar Dataset Analytics Terkait' in html
    assert 'Buka Report' in html
    assert 'Workspace' in html
    assert 'Edit' in html


def test_analytics_dataset_create_page_renders_stage_shell(monkeypatch):
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/analytics/datasets/create')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Buat Dataset Analytics' in html
    assert 'Step 1 — Identitas Dataset' in html
    assert 'Step 2 — Source Picker' in html
    assert 'Step 3 — Contract & Publish' in html
    assert 'Step 4 — Report Readiness' in html
    assert 'Semi-CMS report dinamis' in html


def test_analytics_dataset_workspace_page_renders_operational_shell(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/datasets/7')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Workspace Dataset Analytics' in html
    assert 'Source Summary' in html
    assert 'Versi Dataset' in html
    assert 'Latest Run Snapshot' in html
    assert 'Riwayat Run' in html
    assert 'Edit Report' in html
    assert 'Buka Report' in html


def test_analytics_dataset_report_page_renders_humanized_focus_layout(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/datasets/7/report')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Report Dataset Analytics' in html
    assert 'Workspace Dataset' in html
    assert 'Katalog Report' in html
    assert 'Builder Report' in html
    assert 'Metadata Registry' in html
    assert 'PK Kanwil 2026' in html
    assert 'Narasi laporan tahun aktif.' in html
    assert 'Block Report Aktif' in html
    assert 'metric_cards' in html
    assert 'plotly_timeseries' in html
    assert 'detail_table' in html
    assert 'geo_map' in html
    assert 'narrative' in html
    assert 'Ringkasan KPI' in html
    assert 'Tren Kinerja' in html
    assert 'Tabel Detail Kinerja' in html
    assert 'Sebaran Wilayah' in html
    assert 'Narasi Eksekutif' in html
    assert 'Ke Chart' in html
    assert 'Ke Peta' in html
    assert 'id="analyticsDetailDatasetSelect"' in html
    assert 'id="analyticsDatasetMetricCards"' in html
    assert 'id="analyticsDatasetChart"' in html
    assert 'id="analyticsDatasetDetailTable"' in html
    assert 'id="analyticsDatasetMap"' in html
    assert 'id="analyticsDatasetNarrative"' in html
    assert 'id="analyticsDatasetRunsList"' in html
    assert 'id="analyticsDatasetRunButton"' in html
    assert 'id="analyticsDatasetExecutionStatus"' in html
    assert 'Jembatan Source ke Analytics' in html
    assert 'libs/plotly.js-dist-min/plotly.min.js' in html
    assert 'libs/leaflet/dist/leaflet.js' in html
    assert 'js/pages/analytics-workspace.js' in html
    assert 'analyticsDatasetsUrl' in html
    assert 'analyticsDatasetDetailUrlTemplate' in html
    assert 'analyticsDatasetRunsUrlTemplate' in html
    assert 'analyticsReportConfig' in html
    assert 'supported_period_modes' in html
    assert 'quick_presets' in html
    assert 'Triwulan Ini' in html
    assert 'latest_succeeded_run' in html
    assert 'Cakupan Report' in html
    assert 'Jumlahnya tidak fixed dan mengikuti konfigurasi block pada report ini.' in html
    assert 'reportViewerOptions' in html
    assert 'Kontrak Field Terkurasi' in html
    assert 'Capaian Total' in html
    assert 'Achievement %' in html
    assert 'Metric: capaian_total, achievement_pct' in html
    assert 'Kolom: tanggal, nama_indikator, capaian_total, achievement_pct' in html
    assert 'Fokus narasi: achievement_pct, capaian_total' in html


def test_analytics_dataset_report_page_follows_block_order_from_builder(monkeypatch):
    app = create_app('testing')

    custom_report_item = _make_report_item(dataset_id=7)
    custom_report_item['draft_version'].structure_json['blocks'] = [
        {'type': 'narrative', 'title': 'Narasi Pembuka', 'order': 1},
        {'type': 'detail_table', 'title': 'Tabel Setelah Narasi', 'order': 2},
        {'type': 'plotly_timeseries', 'title': 'Chart Penutup', 'order': 3},
    ]

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr(
        'app.modules.analytics.routes_web.AnalyticsQueryService',
        lambda: StubAnalyticsQueryService(report_item=custom_report_item),
    )

    client = app.test_client()
    response = client.get('/analytics/datasets/7/report')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.index('Narasi Pembuka') < html.index('Tabel Setelah Narasi') < html.index('Chart Penutup')


def test_analytics_report_index_page_renders_catalog(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Report Analytics' in html
    assert 'Katalog Report Semi-CMS' in html
    assert 'PK Kanwil' in html
    assert 'Dataset Wilayah' in html
    assert 'Builder' in html
    assert 'Viewer' in html


def test_analytics_report_create_page_renders_builder(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/create?dataset_id=7')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Buat Report Analytics' in html
    assert 'Builder Report Semi-CMS' in html
    assert 'Dataset Analytics' in html
    assert 'Template / Family Report' in html
    assert 'Default Period Mode' in html
    assert 'name="supported_period_modes"' in html
    assert 'name="quick_presets"' in html
    assert 'Terapkan Template Family' in html
    assert 'Block Editor Manusiawi' in html
    assert 'Advanced JSON' in html
    assert 'Ringkasan Item Report Dinamis' in html
    assert 'Jumlah item pada report tidak fixed.' in html
    assert 'builderDatasetCatalog' in html
    assert 'js-add-report-block' in html
    assert 'Publish Draft' in html


def test_analytics_report_edit_page_renders_builder(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/21/edit')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Edit Report Analytics' in html
    assert 'Builder Report Semi-CMS' in html
    assert 'Template / Family Report' in html
    assert 'PK Kanwil' in html
    assert 'PK Kanwil 2026' in html
    assert 'name="supported_period_modes"' in html
    assert 'name="quick_presets"' in html
    assert 'Plotly Timeseries' in html or 'plotly_timeseries' in html
    assert 'Field Terkurasi Dataset' in html
    assert 'PK -> Dataset Run Binding' in html
    assert 'latest_succeeded_run' in html
    assert 'Block Editor Manusiawi' in html
    assert 'builder-active-version-title' in html
    assert 'report-selection-count' in html
    assert 'toggle-advanced-json-button' in html
    assert 'builderDatasetCatalog' in html
    assert 'js-add-series' in html or 'Tambah Series' in html


def test_analytics_metadata_page_separates_registry_metadata(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/registries/1/metadata')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Metadata Analytics Registry' in html
    assert 'Schema JSON Published' in html
    assert 'Mapping &amp; Source Snapshot' in html or 'Mapping & Source Snapshot' in html
    assert 'Lihat Dataset Terkait' in html
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
    assert 'renderDetailTable' in content
    assert 'renderNarrative' in content
    assert 'renderMap' in content
    assert 'getOrderedReportBlocks' in content
    assert 'resolveConfiguredFieldKeys' in content
    assert 'metric_keys' in content
    assert 'column_keys' in content
    assert 'focus_field_keys' in content
    assert 'latitude_field' in content
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
