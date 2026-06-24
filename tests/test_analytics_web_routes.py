from pathlib import Path
from types import SimpleNamespace

from app import create_app
from app.modules.analytics.routes_web import (
    _extract_formio_fields,
    _serialize_dataset_run_for_report_builder,
    _serialize_dataset_statistics_config,
)


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
    row_snapshots = [
        {'nama_indikator': 'A', 'status_realisasi': 'selesai', 'capaian_total': 1},
        {'nama_indikator': 'B', 'status_realisasi': 'selesai', 'capaian_total': 1},
        {'nama_indikator': 'C', 'status_realisasi': 'selesai', 'capaian_total': 1},
        {'nama_indikator': 'D', 'status_realisasi': 'proses', 'capaian_total': 0},
        {'nama_indikator': 'E', 'status_realisasi': 'belum_jalan', 'capaian_total': 0},
        {'nama_indikator': 'F', 'status_realisasi': 'proses', 'capaian_total': 0},
    ]
    return SimpleNamespace(
        id=run_id,
        status=status,
        result_row_count=6,
        updated_at='2026-06-09T10:00:00+00:00',
        requested_reporting_year=2026,
        result_preview_json=row_snapshots[:3],
        summary_json={
            'row_snapshots': row_snapshots,
            'row_count': 6,
        },
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
                'data_sources': [
                    {
                        'alias': 'pk_target',
                        'label': 'Dataset PK',
                        'dataset_id': dataset_id,
                        'dataset_key': 'dataset-wilayah',
                        'dataset_name': 'Dataset Wilayah',
                        'dataset_version_id': 21,
                        'dataset_version_number': 2,
                        'selection_mode': 'latest_succeeded_run',
                        'curated_fields': [
                            {'key': 'tanggal', 'label': 'Tanggal', 'role': 'date', 'type': 'date'},
                            {'key': 'capaian_total', 'label': 'Capaian Total', 'role': 'metric', 'type': 'integer'},
                            {'key': 'achievement_pct', 'label': 'Achievement %', 'role': 'metric', 'type': 'number'},
                        ],
                    },
                    {
                        'alias': 'renaksi_progress',
                        'label': 'Dataset Renaksi',
                        'dataset_id': 8,
                        'dataset_key': 'dataset-renaksi',
                        'dataset_name': 'Dataset Renaksi',
                        'dataset_version_id': 22,
                        'dataset_version_number': 1,
                        'selection_mode': 'latest_succeeded_run',
                        'curated_fields': [
                            {'key': 'kegiatan', 'label': 'Kegiatan', 'role': 'dimension', 'type': 'string'},
                            {'key': 'status_renaksi', 'label': 'Status Renaksi', 'role': 'dimension', 'type': 'string'},
                            {'key': 'progress_pct', 'label': 'Progress %', 'role': 'metric', 'type': 'number'},
                        ],
                    },
                ],
                'report_items': [
                    {
                        'item_key': 'indikator-1',
                        'name': 'Indikator 1',
                        'description': 'Item uji',
                        'target_value': '100',
                        'datasets': [
                            {
                                'source_mode': 'dataset_driven',
                                'dataset_id': dataset_id,
                                'dataset_version_id': 21,
                                'actual_metric_key': 'capaian_total',
                                'target_metric_key': 'achievement_pct',
                                'aggregation_mode': 'count_value',
                                'target_aggregation_mode': 'count_all',
                                'actual_metric_key': 'status_realisasi',
                                'actual_filter_value': 'selesai',
                                'manual_target': '',
                                'table_column_keys': ['nama_indikator', 'capaian_total'],
                            }
                        ],
                    }
                ],
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Ringkasan KPI', 'data_source_alias': 'pk_target', 'config': {'metric_keys': ['capaian_total', 'achievement_pct']}},
                    {'type': 'plotly_timeseries', 'title': 'Tren Kinerja', 'data_source_alias': 'pk_target', 'config': {'x_key': 'tanggal', 'series': [{'key': 'capaian_total', 'label': 'Capaian Total'}]}},
                    {'type': 'detail_table', 'title': 'Tabel Progress Renaksi', 'data_source_alias': 'renaksi_progress', 'config': {'column_keys': ['kegiatan', 'status_renaksi', 'progress_pct']}},
                    {'type': 'geo_map', 'title': 'Sebaran Wilayah', 'data_source_alias': 'pk_target', 'config': {'latitude_field': 'latitude', 'longitude_field': 'longitude', 'label_field': 'nama_indikator'}},
                    {'type': 'narrative', 'title': 'Narasi Eksekutif', 'data_source_alias': 'renaksi_progress', 'config': {'focus_field_keys': ['progress_pct']}},
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
    assert 'Dataset Analytics' in html
    assert 'Katalog Dataset' in html
    assert 'Buat Dataset' in html
    assert 'Linkage Registry' in html
    assert 'Dataset Wilayah' in html
    assert 'Statistik Dataset' in html
    assert 'Detail Dataset' in html
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
    assert 'Statistik Dataset' in html
    assert 'Detail Dataset' in html
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
    assert 'Dataset Wizard Manusiawi' in html
    assert 'Pilih Source Form' in html
    assert 'Field Picker' in html
    assert 'Derived Metrics / KPI Turunan' in html
    assert 'datasetDerivedMetricBuilderCard' in html
    assert 'derivedMetricSourceFieldSelect' in html
    assert 'count matching value' in html
    assert 'jumlah_realisasi' in html
    assert 'Bangun Contract Otomatis' in html
    assert 'Role Field' in html
    assert 'js-dataset-field-role' in html
    assert 'renderDatasetFieldCards' in html
    assert 'renderDerivedMetricList' in html
    assert 'addDerivedMetricFromInputs' in html
    assert 'source_field' in html
    assert 'match_value' in html
    assert 'updateDerivedMetricSourceOptions' in html
    assert 'derivedMetricRows.forEach' in html
    assert 'syncContractFromFieldCards' in html
    assert 'inferFieldRole' in html
    assert 'Advanced JSON Contract' in html
    assert 'analyticsDatasetBuilderForm' in html
    assert 'analyticsDatasetFormAlert' in html
    assert "addEventListener('submit'" in html
    assert 'createUrl' in html


def test_extract_formio_fields_ignores_textarea_rows_integer_for_dataset_builder():
    schema = {
        'display': 'form',
        'components': [
            {'type': 'textarea', 'key': 'namaRaperdaRaperkada', 'label': 'Nama Raperda/Raperkada', 'rows': 3},
            {'type': 'datetime', 'key': 'tanggal', 'label': 'Tanggal'},
        ],
    }

    fields = _extract_formio_fields(schema)

    assert [field['key'] for field in fields] == ['namaRaperdaRaperkada', 'tanggal']


def test_extract_formio_fields_reads_nested_datagrid_rows_for_dataset_builder():
    schema = {
        'display': 'form',
        'components': [
            {
                'type': 'datagrid',
                'key': 'items',
                'label': 'Items',
                'components': [{'type': 'textfield', 'key': 'nama_item', 'label': 'Nama Item'}],
                'rows': [[{'components': [{'type': 'number', 'key': 'jumlah', 'label': 'Jumlah'}]}]],
            },
        ],
    }

    fields = _extract_formio_fields(schema)

    assert [field['key'] for field in fields] == ['nama_item', 'jumlah', 'items']


def test_analytics_dataset_workspace_page_renders_operational_shell(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/datasets/7')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Detail Dataset Analytics' in html
    assert 'Source Summary' in html
    assert 'Versi Dataset' in html
    assert 'Latest Run Snapshot' in html
    assert 'Riwayat Run' in html
    assert 'Statistik Dataset' in html


def test_analytics_dataset_statistics_page_renders_humanized_focus_layout(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)
    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/datasets/7/statistics')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Statistik Dataset' in html
    assert 'Detail Dataset' in html
    assert 'Metadata Registry' in html
    assert 'Field Dataset Terkurasi' in html
    assert 'metric_cards' in html
    assert 'plotly_timeseries' in html
    assert 'dimension_pie' in html
    assert 'dimension_distribution' in html
    assert 'detail_table' in html
    assert 'narrative' in html
    assert 'KPI Statistik Dataset' in html
    assert 'Chart Waktu Dataset' in html
    assert 'Chart Persentase Dimensi' in html
    assert 'Chart Dimensi Select' in html
    assert 'Tabel Data Hasil Run' in html
    assert 'Narasi Statistik Otomatis' in html
    assert 'Ke Chart' in html
    assert 'id="analyticsDetailDatasetSelect"' in html
    assert 'id="analyticsDatasetMetricCards"' in html
    assert 'id="analyticsDatasetChart"' in html
    assert 'id="analyticsDatasetDimensionSelect"' in html
    assert 'id="analyticsDatasetTimeseriesSplit"' in html
    assert 'id="analyticsDatasetDimensionPieChart"' in html
    assert 'id="analyticsDatasetDetailTable"' in html
    assert 'libs/gridjs/dist/theme/mermaid.min.css' in html
    assert 'libs/gridjs/dist/gridjs.umd.js' in html
    assert 'Preview ringkas memakai Grid.js' in html
    assert 'data-analytics-export="csv"' in html
    assert 'data-analytics-export="json"' in html
    assert 'data-analytics-export="xlsx"' in html
    assert 'id="analyticsDatasetDimensionCharts"' in html
    assert 'id="analyticsDatasetFilterStatus"' not in html
    assert 'id="analyticsDatasetFilterJenis"' not in html
    assert 'id="analyticsDatasetMetricPeriodMode"' not in html
    assert 'id="analyticsDatasetChartType"' not in html
    assert 'libs/xlsx/dist/xlsx.full.min.js' in html
    assert 'id="analyticsDatasetNarrative"' in html
    assert 'id="analyticsDatasetRunsList"' in html
    assert 'id="analyticsDatasetRunButton"' in html
    assert 'id="analyticsDatasetExecutionStatus"' in html
    assert 'id="analyticsDatasetFreshnessStatus"' in html
    assert 'Mengecek freshness source data' in html
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
    assert 'Minggu Ini' in html
    assert 'Bulan Ini' in html
    assert 'Triwulan Ini' in html
    assert 'Triwulan I' in html
    assert 'Triwulan II' in html
    assert 'Triwulan III' in html
    assert 'Triwulan IV' in html
    assert 'Semester Ini' in html
    assert 'Semester 1' in html
    assert 'Semester 2' in html
    assert 'Tahun Ini' in html
    assert 'Semua Range' in html
    assert 'latest_succeeded_run' in html
    assert 'Field Statistik' in html
    assert 'field/metric terkurasi dari dataset aktif' in html
    assert 'reportViewerOptions' in html
    assert 'Kontrak Field Terkurasi' in html
    assert 'Metric: capaian_total, achievement_pct' in html
    assert 'Dimensi: nama_indikator' in html
    assert 'Kolom: tanggal, nama_indikator, latitude, longitude' in html


def test_analytics_dataset_statistics_page_follows_block_order_from_builder(monkeypatch):
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
    response = client.get('/analytics/datasets/7/statistics')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    insight_html = html.split('id="detailReportInsightSection"', 1)[1]
    assert insight_html.index('KPI Statistik Dataset') < insight_html.index('Chart Waktu Dataset') < insight_html.index('Chart Persentase Dimensi') < insight_html.index('Chart Dimensi Select') < insight_html.index('Tabel Data Hasil Run')


def test_analytics_report_index_page_renders_catalog(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Report' in html
    assert 'Tabel Report' in html
    assert 'Nama Report' in html
    assert 'PK Kanwil' in html
    assert 'Edit' in html
    assert 'Delete' in html
    assert 'Dataset Wilayah' not in html
    assert 'Statistik Dataset' not in html


def test_analytics_report_create_page_renders_builder(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/create?dataset_id=7')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Tambah Report' in html
    assert 'Edit Report' in html
    assert 'Nama Report' in html
    assert 'Deskripsi Singkat' in html
    assert 'Item / Indikator Report' in html
    assert 'Nama Indikator' in html
    assert 'Nilai (Capaian)' in html
    assert 'Action' in html
    assert 'report_items_json' in html
    assert 'reportAchievementChart' in html
    assert 'analyticsReportFormAlert' in html
    assert 'showFormMessage' in html
    assert 'alert(' not in html
    assert 'Publish Draft' in html


def test_analytics_report_edit_page_renders_builder(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/21/edit')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Edit Report' in html
    assert 'PK Kanwil' in html
    assert 'Buka Statistik Dataset' not in html
    assert 'Nama Report' in html
    assert 'Deskripsi Singkat' in html
    assert 'Item / Indikator Report' in html
    assert 'Nama Indikator' in html
    assert 'Nilai (Capaian)' in html
    assert 'Target' in html
    assert 'Action' in html
    assert 'Chart Persentase Capaian Item' in html
    assert 'reportAchievementChart' in html
    assert 'Tambah Indikator' in html
    assert 'add-report-indicator-button' in html
    assert 'Tambah Dataset' not in html
    assert '/analytics/reports/${reportId || \'new\'}/items/' in html
    assert 'showFormMessage' in html


def test_serialize_dataset_run_for_report_builder_keeps_all_row_snapshots_for_counts():
    rows = [{'jenis': 'Raperda (Pemda)', 'index': index} for index in range(104)]
    run = SimpleNamespace(
        id=15,
        status='succeeded',
        result_row_count=104,
        summary_json={'row_snapshots': rows, 'row_count': 104},
        result_preview_json=rows[:10],
    )

    payload = _serialize_dataset_run_for_report_builder(run)

    assert payload is not None
    assert payload['result_row_count'] == 104
    assert len(payload['row_snapshots']) == 104


def test_dataset_statistics_config_keeps_derived_count_metric_contract():
    dataset = SimpleNamespace(id=4, dataset_key='harmon-2026', name='Harmonisasi 2026')
    version = SimpleNamespace(
        id=9,
        version_number=3,
        output_schema_json=[
            {'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'},
            {'key': 'hasil', 'label': 'Hasil', 'type': 'select'},
        ],
        dimension_definitions_json=[
            {'key': 'hasil', 'label': 'Hasil', 'type': 'select'},
        ],
        metric_definitions_json=[
            {
                'key': 'jumlah_realisasi',
                'label': 'Jumlah Realisasi',
                'type': 'integer',
                'source_field': 'hasil',
                'aggregation': 'count_matching_value',
                'match_value': 'selesai',
            },
            {
                'key': 'total_data',
                'label': 'Total Data',
                'type': 'integer',
                'aggregation': 'count',
            },
        ],
    )

    config = _serialize_dataset_statistics_config(dataset, version)

    metric_block = next(block for block in config['blocks'] if block['type'] == 'metric_cards')
    chart_block = next(block for block in config['blocks'] if block['type'] == 'plotly_timeseries')
    dimension_block = next(block for block in config['blocks'] if block['type'] == 'dimension_distribution')
    assert 'hasil' in dimension_block['config']['dimension_keys']
    assert metric_block['config']['metric_keys'] == ['jumlah_realisasi', 'total_data']
    assert metric_block['config']['metric_definitions'][0]['source_field'] == 'hasil'
    assert metric_block['config']['metric_definitions'][0]['aggregation'] == 'count_matching_value'
    assert chart_block['config']['series'][0]['key'] == 'jumlah_realisasi'
    assert chart_block['config']['series'][0]['match_value'] == 'selesai'


def test_analytics_report_item_edit_page_renders_dataset_and_manual_input_builder(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)

    client = app.test_client()
    response = client.get('/analytics/reports/21/items/1/edit')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Edit Item Report' in html
    assert 'Tambah Dataset' in html
    assert 'Dataset / Manual Input Item' in html
    assert 'Nilai / Metric (Capaian)' in html
    assert 'Manual input / tanpa dataset' in html
    assert 'sum' in html
    assert 'average' in html
    assert 'count matching value' in html
    assert 'target = count semua record' in html
    assert 'status_realisasi' in html
    assert 'selesai' in html
    assert 'proses' in html
    assert 'belum_jalan' in html
    assert 'row_snapshots' in html
    assert 'js-source-actual-value' in html
    assert 'js-source-target-value' in html
    assert 'manual' in html
    assert 'Chart Dataset / Manual' in html
    assert 'Tabel Data Dataset' in html
    assert 'js-source-actual' in html
    assert 'js-source-manual-value' in html
    assert 'js-source-manual-target' in html
    assert 'js-source-condition-field' not in html
    assert 'js-source-target-aggregation' in html


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
    assert 'analyticsDatasetFreshnessStatus' in body
    assert 'Freshness source' in body
    assert 'Refresh Dataset dari Source Terbaru' in body
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
    assert 'resolveChartXKey' in content
    assert 'renderMetricCards' in content
    assert 'renderChart' in content
    assert 'renderDetailTable' in content
    assert 'exportDetailRows' in content
    assert "format === 'xlsx'" in content
    assert 'window.XLSX.writeFile' in content
    assert 'datasetChartType' in content
    assert 'Plotly.purge' in content
    assert 'lastChartType' in content
    assert 'downloadBlob' in content
    assert 'data-analytics-export' in content
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
    assert 'quarter_1' in content
    assert 'quarter_2' in content
    assert 'quarter_3' in content
    assert 'quarter_4' in content
    assert 'current_semester' in content
    assert 'semester_1' in content
    assert 'semester_2' in content
    assert 'current_year' in content
    assert 'full_range' in content
    assert "series.key === 'total'" in content
    assert 'analyticsDatasetDimensionSelect' in content
    assert 'analyticsDatasetDimensionPieChart' in content
    assert 'aggregateRowsByPeriodAndDimension' in content
    assert 'splitTimeseriesByDimension' in content
    assert 'metric_definitions' in content
    assert 'count_matching_value' in content
    assert 'source_field' in content
    assert 'rowMatchesMetricValue' in content
    assert 'summarizeMetricSeriesValue' in content
    assert 'getPlotlyRenderOptions' in content
    assert 'displayModeBar: true' in content
    assert 'toImageButtonOptions' in content
    assert 'scrollZoom: true' in content
    assert 'window.gridjs' in content
    assert 'new Grid.Grid' in content
    assert 'pagination' in content
    assert 'limit: 10' in content
    assert 'Export CSV/XLSX/JSON tetap mengambil seluruh baris aktif' in content


def test_analytics_dataset_report_shortcut_opens_multi_dataset_builder(monkeypatch):
    app = create_app('testing')

    monkeypatch.setattr('app.modules.analytics.routes_web.AnalyticsQueryService', StubAnalyticsQueryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryService', StubDataRegistryService)
    monkeypatch.setattr('app.modules.analytics.routes_web.DataRegistryVersionService', StubDataRegistryVersionService)

    client = app.test_client()
    response = client.get('/analytics/datasets/7/report')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Tambah Report' in html or 'Edit Report' in html
    assert 'Item / Indikator Report' in html
    assert 'report_items_json' in html
    assert 'data_sources_json' in html
    assert 'blocks_json' in html
    assert 'reportAchievementChart' in html


def test_analytics_report_builder_template_is_item_dataset_aware():
    content = Path('app/templates/pages/analytics/report_form.html').read_text()

    assert 'report_items_json' in content
    assert 'const pageMode' in content
    assert 'reportAchievementChart' in content
    assert 'achievementPct' in content
    assert 'itemEditUrl' in content
    assert 'createDefaultItem' in content
    assert 'syncReportItemsJson' in content
    assert 'Tambah Indikator' in content
    assert 'Nilai (Capaian)' in content
    assert 'computed_actual_value' in content
    assert 'target_aggregation_mode' in content
    assert 'count_value' in content
    assert 'Tambah Dataset' not in content


def test_analytics_report_item_form_persists_computed_values_for_summary_page():
    content = Path('app/templates/pages/analytics/report_item_form.html').read_text()

    assert 'enrichComputedValues' in content
    assert 'computed_actual_value' in content
    assert 'computed_target_value' in content
    assert 'target_aggregation_mode' in content
    assert 'count_value' in content


def test_analytics_report_item_form_manual_inputs_do_not_rerender_on_each_keystroke():
    content = Path('app/templates/pages/analytics/report_item_form.html').read_text()

    assert 'function updateSourceState' in content
    assert 'function updateManualPreview' in content
    assert 'js-source-actual-preview' in content
    assert 'js-source-target-preview' in content
    assert "if (event.target.classList.contains('js-source-manual-value')) { const source = updateSourceState" in content
    assert "if (event.target.classList.contains('js-source-manual-target')) { const source = updateSourceState" in content


def test_analytics_workspace_source_js_loads_rows_per_report_data_source():
    js_path = Path('app/src/js/pages/analytics-workspace.js')
    content = js_path.read_text()

    assert 'reportSourceDetails' in content
    assert 'reportSourceRuns' in content
    assert 'loadReportDataSources' in content
    assert 'fetchDatasetDetailForSource' in content
    assert 'fetchDatasetRunsForSource' in content
    assert 'getRowsForBlock' in content
    assert 'currentFilteredRowsByBlock' in content
    assert 'renderDetailTable(state.currentFilteredRowsByBlock.detail_table)' in content
    assert 'renderMetricCards(state.currentFilteredRowsByBlock.metric_cards, summaryJson)' in content
