from types import SimpleNamespace

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def make_report_definition(**overrides):
    defaults = {
        'id': 21,
        'uuid': 'report-def-uuid',
        'report_key': 'pk-kanwil',
        'name': 'PK Kanwil',
        'description': 'Laporan kinerja kanwil.',
        'report_type': 'performance_report',
        'category_key': 'pk',
        'status': 'active',
        'is_active': True,
        'settings_json': {},
        'tags_json': [],
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_report_version(**overrides):
    defaults = {
        'id': 31,
        'uuid': 'report-version-uuid',
        'report_definition_id': 21,
        'version_number': 1,
        'status': 'draft',
        'is_current_draft': True,
        'is_current_published': False,
        'title': 'PK 2026',
        'meta_description': 'Narasi laporan tahun aktif.',
        'structure_json': {'sections': []},
        'narrative_guidance_json': {'summary_prompt': 'Ringkas capaian.'},
        'published_at': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_indicator_definition(**overrides):
    defaults = {
        'id': 41,
        'uuid': 'indicator-def-uuid',
        'indicator_key': 'renaksi.tindak_lanjut',
        'indicator_code': 'REN-001',
        'name': 'Tindak lanjut Renaksi',
        'description': 'Indikator tindak lanjut.',
        'source_mode': 'manual_input',
        'calculation_type': 'checklist_completion',
        'target_source_type': 'manual_central_target',
        'status': 'active',
        'is_active': True,
        'settings_json': {},
        'tags_json': [],
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_indicator_version(**overrides):
    defaults = {
        'id': 51,
        'uuid': 'indicator-version-uuid',
        'indicator_definition_id': 41,
        'version_number': 1,
        'dataset_id': None,
        'dataset_version_id': None,
        'status': 'draft',
        'is_current_draft': True,
        'is_current_published': False,
        'period_mode': 'yearly',
        'aggregation_strategy': 'last_value',
        'unit_label': '%',
        'meta_description': 'Narasi indikator.',
        'formula_json': {},
        'target_config_json': {'target_value': 100},
        'narrative_guidance_json': {'focus': ['capaian', 'kendala']},
        'threshold_rules_json': [],
        'published_at': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_report_mapping(**overrides):
    defaults = {
        'id': 61,
        'uuid': 'report-mapping-uuid',
        'report_version_id': 31,
        'indicator_version_id': 51,
        'item_order': 1,
        'display_label': 'Tindak lanjut',
        'section_key': 'renaksi',
        'config_json': {},
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_indicator_result(**overrides):
    defaults = {
        'id': 71,
        'uuid': 'indicator-result-uuid',
        'indicator_version_id': 51,
        'dataset_run_id': 900,
        'reporting_year': 2026,
        'reporting_period_id': 3,
        'status': 'draft',
        'completion_status': 'completed',
        'measured_value': '42.0000',
        'target_value': '50.0000',
        'achievement_percentage': '84.0000',
        'qualitative_summary': 'Capaian meningkat.',
        'constraint_notes': 'Masih ada hambatan.',
        'narrative_context_json': {'highlights': ['perbaikan']},
        'source_snapshot_json': {
            'source_mode': 'dataset_driven',
            'dataset_id': 77,
            'dataset_version_id': 78,
            'dataset_run_id': 900,
            'indicator_version_id': 51,
        },
        'calculated_at': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_progress_entry(**overrides):
    defaults = {
        'id': 81,
        'uuid': 'progress-entry-uuid',
        'indicator_version_id': 51,
        'reporting_year': 2026,
        'reporting_period_id': 3,
        'status': 'completed',
        'progress_percent': '85.0000',
        'qualitative_summary': 'Ringkasan progres.',
        'constraint_notes': 'Butuh koordinasi lintas unit.',
        'narrative_context_json': {'risks': ['verifikasi']},
        'summary_json': {'completed_items': 2, 'total_items': 3},
        'items': [
            SimpleNamespace(
                id=1,
                uuid='progress-item-uuid-1',
                progress_entry_id=81,
                item_order=1,
                status='done',
                title='Konsolidasi data',
                description='Selesai.',
                narrative_context_json={},
                created_at=None,
                updated_at=None,
            )
        ],
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def assert_validation_error(response, expected_message):
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert expected_message in payload['message']
    assert payload['data']['error_type'] == 'validation_error'



def test_analytics_api_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/api/v1/analytics/reports',
        '/api/v1/analytics/reports/<int:report_definition_id>/versions',
        '/api/v1/analytics/report-versions/<int:version_id>/publish',
        '/api/v1/analytics/indicators',
        '/api/v1/analytics/indicators/<int:indicator_definition_id>/versions',
        '/api/v1/analytics/indicator-versions/<int:version_id>/publish',
        '/api/v1/analytics/report-versions/<int:report_version_id>/indicators',
        '/api/v1/analytics/indicator-results',
        '/api/v1/analytics/indicator-progress-entries',
        '/api/v1/analytics/indicator-progress-entries/<int:progress_entry_id>/sync-result',
    ]

    for route in expected_routes:
        assert route in rules



def test_post_analytics_report_returns_created_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsReportService:
        def create_report_definition(self, data, actor=None):
            return make_report_definition(report_key=data['report_key'], name=data['name'])

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsReportService', StubAnalyticsReportService)

    response = client.post(
        '/api/v1/analytics/reports',
        json={
            'report_key': 'pk-kanwil',
            'name': 'PK Kanwil',
            'report_type': 'performance_report',
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['report']['report_key'] == 'pk-kanwil'
    assert payload['data']['report']['name'] == 'PK Kanwil'



def test_post_analytics_indicator_version_returns_validation_error_for_invalid_source_mode(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsIndicatorService:
        def create_indicator_version(self, indicator_definition_id, data, actor=None):
            raise ValueError('Indicator dataset_driven wajib memiliki dataset_id dan dataset_version_id.')

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsIndicatorService', StubAnalyticsIndicatorService)

    response = client.post(
        '/api/v1/analytics/indicators/41/versions',
        json={
            'period_mode': 'yearly',
            'aggregation_strategy': 'sum',
        },
    )

    assert_validation_error(response, 'wajib memiliki dataset_id dan dataset_version_id')



def test_post_attach_indicator_returns_validation_error_for_unpublished_indicator(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsIndicatorService:
        def attach_indicator_to_report_version(self, report_version_id, indicator_version_id, data=None, actor=None):
            raise ValueError('Hanya indicator version published yang boleh di-attach ke report version.')

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsIndicatorService', StubAnalyticsIndicatorService)

    response = client.post(
        '/api/v1/analytics/report-versions/31/indicators',
        json={
            'indicator_version_id': 51,
            'item_order': 1,
            'display_label': 'Tindak lanjut',
        },
    )

    assert_validation_error(response, 'indicator version published')



def test_post_indicator_result_returns_payload_with_source_trace(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsIndicatorResultService:
        def record_result(self, data, actor=None):
            return make_indicator_result(
                indicator_version_id=data['indicator_version_id'],
                dataset_run_id=data['dataset_run_id'],
            )

    monkeypatch.setattr(
        'app.api.v1.analytics.routes.AnalyticsIndicatorResultService',
        StubAnalyticsIndicatorResultService,
    )

    response = client.post(
        '/api/v1/analytics/indicator-results',
        json={
            'indicator_version_id': 51,
            'dataset_run_id': 900,
            'reporting_year': 2026,
            'reporting_period_id': 3,
            'measured_value': '42.0000',
            'target_value': '50.0000',
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['result']['dataset_run_id'] == 900
    assert payload['data']['result']['source_snapshot_json']['dataset_run_id'] == 900



def test_post_progress_entry_and_sync_result_return_serialized_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsIndicatorResultService:
        def record_progress_entry(self, data, actor=None):
            return make_progress_entry(
                indicator_version_id=data['indicator_version_id'],
                reporting_year=data['reporting_year'],
                reporting_period_id=data['reporting_period_id'],
            )

        def sync_result_from_progress(self, progress_entry_id, actor=None):
            return make_indicator_result(id=91, indicator_version_id=51)

    monkeypatch.setattr(
        'app.api.v1.analytics.routes.AnalyticsIndicatorResultService',
        StubAnalyticsIndicatorResultService,
    )

    create_response = client.post(
        '/api/v1/analytics/indicator-progress-entries',
        json={
            'indicator_version_id': 51,
            'reporting_year': 2026,
            'reporting_period_id': 3,
            'items': [
                {
                    'item_order': 1,
                    'status': 'done',
                    'title': 'Konsolidasi data',
                }
            ],
        },
    )

    assert create_response.status_code == 201
    create_payload = create_response.get_json()
    assert create_payload['success'] is True
    assert create_payload['data']['progress_entry']['indicator_version_id'] == 51
    assert create_payload['data']['progress_entry']['items'][0]['title'] == 'Konsolidasi data'

    sync_response = client.post('/api/v1/analytics/indicator-progress-entries/81/sync-result', json={})
    assert sync_response.status_code == 200
    sync_payload = sync_response.get_json()
    assert sync_payload['success'] is True
    assert sync_payload['data']['result']['id'] == 91



def test_get_analytics_reports_returns_workspace_summary(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def list_reports(self):
            return [
                {
                    'report': make_report_definition(),
                    'draft_version': make_report_version(id=31, version_number=2, status='draft'),
                    'published_version': make_report_version(
                        id=32,
                        version_number=1,
                        status='published',
                        is_current_draft=False,
                        is_current_published=True,
                    ),
                    'indicator_mapping_count': 3,
                }
            ]

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/reports')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['reports'][0]['report']['report_key'] == 'pk-kanwil'
    assert payload['data']['reports'][0]['draft_version']['version_number'] == 2
    assert payload['data']['reports'][0]['indicator_mapping_count'] == 3



def test_get_analytics_report_detail_returns_versions_and_mappings(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def get_report_workspace(self, report_definition_id):
            return {
                'report': make_report_definition(id=report_definition_id),
                'draft_version': make_report_version(id=31, version_number=2, status='draft'),
                'published_version': make_report_version(
                    id=32,
                    version_number=1,
                    status='published',
                    is_current_draft=False,
                    is_current_published=True,
                ),
                'versions': [
                    make_report_version(id=31, version_number=2, status='draft'),
                    make_report_version(id=32, version_number=1, status='published'),
                ],
                'indicator_mappings': [
                    {
                        'mapping': make_report_mapping(id=61),
                        'indicator_version': make_indicator_version(id=51, status='published'),
                        'indicator_definition': make_indicator_definition(id=41),
                    }
                ],
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/reports/21')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['report']['id'] == 21
    assert len(payload['data']['versions']) == 2
    assert payload['data']['indicator_mappings'][0]['mapping']['indicator_version_id'] == 51
    assert payload['data']['indicator_mappings'][0]['indicator_definition']['indicator_key'] == 'renaksi.tindak_lanjut'



def test_get_analytics_indicators_returns_workspace_summary(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def list_indicators(self):
            return [
                {
                    'indicator': make_indicator_definition(),
                    'draft_version': make_indicator_version(id=51, version_number=2, status='draft'),
                    'published_version': make_indicator_version(
                        id=52,
                        version_number=1,
                        status='published',
                        is_current_draft=False,
                        is_current_published=True,
                    ),
                    'latest_result': make_indicator_result(id=71),
                    'latest_progress_entry': make_progress_entry(id=81),
                }
            ]

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/indicators')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['indicators'][0]['indicator']['indicator_key'] == 'renaksi.tindak_lanjut'
    assert payload['data']['indicators'][0]['published_version']['status'] == 'published'
    assert payload['data']['indicators'][0]['latest_result']['id'] == 71



def test_get_analytics_indicator_detail_returns_results_and_progress(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def get_indicator_workspace(self, indicator_definition_id):
            return {
                'indicator': make_indicator_definition(id=indicator_definition_id),
                'draft_version': make_indicator_version(id=51, version_number=2, status='draft'),
                'published_version': make_indicator_version(
                    id=52,
                    version_number=1,
                    status='published',
                    is_current_draft=False,
                    is_current_published=True,
                ),
                'versions': [
                    make_indicator_version(id=51, version_number=2, status='draft'),
                    make_indicator_version(id=52, version_number=1, status='published'),
                ],
                'results': [make_indicator_result(id=71)],
                'progress_entries': [make_progress_entry(id=81)],
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/indicators/41')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['indicator']['id'] == 41
    assert payload['data']['results'][0]['source_snapshot_json']['dataset_run_id'] == 900
    assert payload['data']['progress_entries'][0]['items'][0]['title'] == 'Konsolidasi data'



def test_get_analytics_indicator_results_returns_filtered_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()
    captured = {}

    class StubAnalyticsQueryService:
        def list_indicator_results(self, indicator_version_id=None, reporting_year=None, reporting_period_id=None, limit=50):
            captured['indicator_version_id'] = indicator_version_id
            captured['reporting_year'] = reporting_year
            captured['reporting_period_id'] = reporting_period_id
            captured['limit'] = limit
            return [make_indicator_result(id=71, indicator_version_id=indicator_version_id or 51)]

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/indicator-results?indicator_version_id=51&reporting_year=2026&reporting_period_id=3&limit=10')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['results'][0]['indicator_version_id'] == 51
    assert captured == {
        'indicator_version_id': 51,
        'reporting_year': 2026,
        'reporting_period_id': 3,
        'limit': 10,
    }
