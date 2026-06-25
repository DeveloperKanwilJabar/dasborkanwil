from types import SimpleNamespace

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def make_dataset(**overrides):
    defaults = {
        'id': 11,
        'uuid': 'dataset-uuid',
        'dataset_key': 'submission-ringkas',
        'name': 'Submission Ringkas',
        'description': 'Dataset ringkas submission.',
        'source_domain': 'submission',
        'source_type': 'aggregated_submission_fact',
        'primary_source_ref': 'form:FORM-A',
        'status': 'active',
        'is_active': True,
        'is_year_scoped': True,
        'default_reporting_year_mode': 'active_year',
        'owner_scope_type': 'kanwil',
        'owner_scope_code': 'JBR',
        'owner_scope_name': 'Jawa Barat',
        'owner_scope_path': ['nasional', 'jbr'],
        'settings_json': {},
        'tags_json': [],
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_dataset_version(**overrides):
    defaults = {
        'id': 22,
        'uuid': 'dataset-version-uuid',
        'dataset_id': 11,
        'version_number': 2,
        'status': 'published',
        'is_current_draft': False,
        'is_current_published': True,
        'source_contract_json': {'form_codes': ['FORM-A']},
        'query_spec_json': {'select': ['count(*)']},
        'transform_spec_json': {'steps': []},
        'join_registry_spec_json': [],
        'grain_key': 'per_scope_per_year',
        'output_schema_json': [{'key': 'total'}],
        'dimension_definitions_json': [],
        'metric_definitions_json': [{'key': 'total'}],
        'default_filters_json': {},
        'sort_spec_json': [],
        'freshness_source_type': 'submissions.submitted_at',
        'freshness_source_ref': None,
        'freshness_strategy': 'max_timestamp',
        'freshness_policy_json': {},
        'publish_notes': None,
        'published_at': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_dataset_run(**overrides):
    defaults = {
        'id': 33,
        'uuid': 'dataset-run-uuid',
        'dataset_id': 11,
        'dataset_version_id': 22,
        'run_key': 'dataset-run-001',
        'trigger_type': 'manual',
        'trigger_ref': None,
        'requested_reporting_year': 2026,
        'requested_reporting_period_id': None,
        'requested_filters_json': {'scope_code': 'JBR'},
        'status': 'running',
        'started_at': None,
        'finished_at': None,
        'duration_ms': None,
        'source_watermark': None,
        'freshness_status': 'unknown',
        'source_snapshot_json': {},
        'freshness_evaluated_at': None,
        'result_row_count': None,
        'result_schema_json': [],
        'result_preview_json': [],
        'materialization_ref': None,
        'summary_json': {},
        'error_code': None,
        'error_message': None,
        'error_detail_json': {},
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_dataset_run_api_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/api/v1/analytics/datasets',
        '/api/v1/analytics/datasets/<int:dataset_id>',
        '/api/v1/analytics/dataset-versions/<int:version_id>/publish',
        '/api/v1/analytics/datasets/<int:dataset_id>/runs',
        '/api/v1/analytics/datasets/<int:dataset_id>/versions/<int:dataset_version_id>/runs',
        '/api/v1/analytics/runs/<int:run_id>',
    ]

    for route in expected_routes:
        assert route in rules


def test_create_analytics_dataset_returns_dataset_and_draft(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsDatasetService:
        def create_dataset_bundle(self, data, actor=None):
            assert data['dataset']['dataset_key'] == 'indikator-pk'
            assert data['draft_version']['source_contract_json']['selected_fields'] == ['nama_indikator', 'target']
            return {
                'dataset': make_dataset(id=77, dataset_key='indikator-pk', name='Dataset PK'),
                'draft_version': make_dataset_version(
                    id=88,
                    dataset_id=77,
                    status='draft',
                    is_current_draft=True,
                    is_current_published=False,
                    source_contract_json={'selected_fields': ['nama_indikator', 'target']},
                    metric_definitions_json=[{'key': 'capaian'}],
                    output_schema_json=[{'key': 'nama_indikator'}, {'key': 'capaian'}],
                ),
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsDatasetService', StubAnalyticsDatasetService)

    response = client.post(
        '/api/v1/analytics/datasets',
        json={
            'dataset': {'dataset_key': 'indikator-pk'},
            'draft_version': {
                'source_contract_json': {'selected_fields': ['nama_indikator', 'target']},
                'metric_definitions_json': [{'key': 'capaian'}],
                'output_schema_json': [{'key': 'nama_indikator'}, {'key': 'capaian'}],
            },
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['dataset']['id'] == 77
    assert payload['data']['draft_version']['status'] == 'draft'


def test_update_analytics_dataset_returns_dataset_and_draft(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsDatasetService:
        def update_dataset_bundle(self, dataset_id, data, actor=None):
            assert dataset_id == 11
            assert data['dataset']['name'] == 'Dataset PK Revisi'
            return {
                'dataset': make_dataset(id=11, name='Dataset PK Revisi'),
                'draft_version': make_dataset_version(
                    id=22,
                    dataset_id=11,
                    status='draft',
                    is_current_draft=True,
                    is_current_published=False,
                    metric_definitions_json=[{'key': 'capaian'}],
                    output_schema_json=[{'key': 'nama_indikator'}, {'key': 'capaian'}],
                ),
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsDatasetService', StubAnalyticsDatasetService)

    response = client.put(
        '/api/v1/analytics/datasets/11',
        json={
            'dataset': {'name': 'Dataset PK Revisi'},
            'draft_version': {
                'source_contract_json': {'selected_fields': ['nama_indikator', 'target']},
                'metric_definitions_json': [{'key': 'capaian'}],
                'output_schema_json': [{'key': 'nama_indikator'}, {'key': 'capaian'}],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['dataset']['name'] == 'Dataset PK Revisi'
    assert payload['data']['draft_version']['id'] == 22


def test_publish_analytics_dataset_version_returns_published_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsDatasetService:
        def publish_dataset_version(self, version_id, actor=None):
            assert version_id == 22
            return make_dataset_version(
                id=22,
                status='published',
                is_current_draft=False,
                is_current_published=True,
            )

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsDatasetService', StubAnalyticsDatasetService)

    response = client.post('/api/v1/analytics/dataset-versions/22/publish', json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['dataset_version']['status'] == 'published'


def test_get_analytics_datasets_returns_summary_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def list_datasets(self):
            return [
                {
                    'dataset': make_dataset(),
                    'draft_version': None,
                    'published_version': make_dataset_version(),
                    'latest_run': make_dataset_run(status='succeeded', result_row_count=12),
                }
            ]

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/datasets')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['datasets'][0]['dataset']['dataset_key'] == 'submission-ringkas'
    assert payload['data']['datasets'][0]['published_version']['version_number'] == 2
    assert payload['data']['datasets'][0]['latest_run']['status'] == 'succeeded'


def test_get_analytics_dataset_detail_returns_versions_and_runs(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def get_dataset_workspace(self, dataset_id, auto_enqueue_stale=False, actor=None):
            assert auto_enqueue_stale is False
            return {
                'dataset': make_dataset(id=dataset_id),
                'draft_version': None,
                'published_version': make_dataset_version(),
                'versions': [make_dataset_version()],
                'runs': [make_dataset_run(status='failed', error_code='QUERY_TIMEOUT')],
                'freshness': {
                    'status': 'stale',
                    'is_stale': True,
                    'source_watermark': '2026-06-24T10:00:00+00:00',
                    'run_watermark': '2026-06-24T09:00:00+00:00',
                },
                'auto_refresh': {},
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/datasets/11')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['dataset']['id'] == 11
    assert payload['data']['versions'][0]['version_number'] == 2
    assert payload['data']['runs'][0]['error_code'] == 'QUERY_TIMEOUT'
    assert payload['data']['freshness']['is_stale'] is True
    assert payload['data']['freshness']['source_watermark'] == '2026-06-24T10:00:00+00:00'


def test_get_analytics_dataset_detail_can_request_auto_enqueue_stale(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def get_dataset_workspace(self, dataset_id, auto_enqueue_stale=False, actor=None):
            assert dataset_id == 11
            assert auto_enqueue_stale is True
            return {
                'dataset': make_dataset(id=dataset_id),
                'draft_version': None,
                'published_version': make_dataset_version(),
                'versions': [make_dataset_version()],
                'runs': [make_dataset_run(id=44, status='queued')],
                'freshness': {'status': 'stale', 'is_stale': True},
                'auto_refresh': {
                    'attempted': True,
                    'queued': True,
                    'run_id': 44,
                    'dispatch': {'queued': True},
                },
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/datasets/11?auto_enqueue_stale=1')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['data']['auto_refresh']['queued'] is True
    assert payload['data']['auto_refresh']['run_id'] == 44


def test_get_analytics_dataset_runs_returns_run_history(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def list_dataset_runs(self, dataset_id):
            assert dataset_id == 11
            return [
                make_dataset_run(id=33, run_key='dataset-run-001', status='succeeded', result_row_count=12),
                make_dataset_run(id=34, run_key='dataset-run-002', status='failed', error_code='QUERY_TIMEOUT'),
            ]

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/datasets/11/runs')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert len(payload['data']['runs']) == 2
    assert payload['data']['runs'][1]['error_code'] == 'QUERY_TIMEOUT'


def test_post_analytics_dataset_run_returns_queued_refresh_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsDatasetRunService:
        def enqueue_run(self, dataset_id, dataset_version_id, data, actor=None):
            assert dataset_id == 11
            assert dataset_version_id == 22
            return {
                'run': make_dataset_run(
                    dataset_id=dataset_id,
                    dataset_version_id=dataset_version_id,
                    status='queued',
                    requested_reporting_year=data['requested_reporting_year'],
                    requested_filters_json=data['requested_filters_json'],
                ),
                'dispatch': {'queued': True, 'task_id': 'celery-task-1', 'error': None},
            }

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsDatasetRunService', StubAnalyticsDatasetRunService)

    response = client.post(
        '/api/v1/analytics/datasets/11/versions/22/runs',
        json={
            'trigger_type': 'manual',
            'requested_reporting_year': 2026,
            'requested_filters_json': {'scope_code': 'JBR'},
        },
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['run']['status'] == 'queued'
    assert payload['data']['run']['dataset_version_id'] == 22
    assert payload['data']['dispatch']['task_id'] == 'celery-task-1'


def test_get_analytics_run_detail_returns_observability_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubAnalyticsQueryService:
        def get_dataset_run_detail(self, run_id):
            assert run_id == 33
            return make_dataset_run(
                id=33,
                status='failed',
                result_row_count=10,
                summary_json={'freshness': 'stale'},
                error_code='QUERY_TIMEOUT',
                error_message='Dataset execution timed out.',
            )

    monkeypatch.setattr('app.api.v1.analytics.routes.AnalyticsQueryService', StubAnalyticsQueryService)

    response = client.get('/api/v1/analytics/runs/33')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['run']['status'] == 'failed'
    assert payload['data']['run']['result_row_count'] == 10
    assert payload['data']['run']['summary_json'] == {'freshness': 'stale'}
    assert payload['data']['run']['error_code'] == 'QUERY_TIMEOUT'
