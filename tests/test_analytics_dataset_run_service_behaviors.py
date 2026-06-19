from types import SimpleNamespace

from app import create_app
from app.modules.analytics.models import (
    AnalyticsDataset,
    AnalyticsDatasetRun,
    AnalyticsDatasetVersion,
)


class SaveMixin:
    def __init__(self):
        self.saved = []
        self.next_id = 1

    def save(self, obj):
        if getattr(obj, 'id', None) is None:
            obj.id = self.next_id
            self.next_id += 1
        self.saved.append(obj)
        return obj


class StubDatasetRepository(SaveMixin):
    def __init__(self, datasets=None):
        super().__init__()
        self.datasets = {item.id: item for item in (datasets or []) if getattr(item, 'id', None) is not None}

    def save(self, obj):
        obj = super().save(obj)
        self.datasets[obj.id] = obj
        return obj

    def get_by_id(self, dataset_id):
        return self.datasets.get(dataset_id)


class StubDatasetVersionRepository(SaveMixin):
    def __init__(self, versions=None):
        super().__init__()
        self.versions = []
        self.archived_calls = []
        for version in versions or []:
            self.save(version)

    def save(self, obj):
        obj = super().save(obj)
        if obj not in self.versions:
            self.versions.append(obj)
        return obj

    def get_by_id(self, version_id):
        for version in self.versions:
            if version.id == version_id:
                return version
        return None

    def get_next_version_number(self, dataset_id):
        numbers = [
            version.version_number
            for version in self.versions
            if version.dataset_id == dataset_id
        ]
        return (max(numbers) if numbers else 0) + 1

    def archive_published_others(self, dataset_id, except_version_id=None):
        self.archived_calls.append(
            {
                'dataset_id': dataset_id,
                'except_version_id': except_version_id,
            }
        )
        archived = []
        for version in self.versions:
            if version.dataset_id != dataset_id:
                continue
            if except_version_id is not None and version.id == except_version_id:
                continue
            if version.is_current_published:
                version.is_current_published = False
                version.is_current_draft = False
                version.status = AnalyticsDatasetVersion.STATUS_ARCHIVED
                archived.append(version)
        return archived


class StubDatasetRunRepository(SaveMixin):
    def __init__(self, runs=None):
        super().__init__()
        self.runs = []
        for run in runs or []:
            self.save(run)

    def save(self, obj):
        obj = super().save(obj)
        if obj not in self.runs:
            self.runs.append(obj)
        return obj

    def get_by_id(self, run_id):
        for run in self.runs:
            if run.id == run_id:
                return run
        return None


def test_create_publish_dataset_version_archives_previous_versions():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetService

        actor = SimpleNamespace(id=9, uuid='actor-uuid')
        dataset = AnalyticsDataset(
            id=11,
            uuid='dataset-uuid',
            dataset_key='submission-ringkas',
            name='Submission Ringkas',
            source_domain=AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
            source_type=AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
            status=AnalyticsDataset.STATUS_DRAFT,
        )
        old_version = AnalyticsDatasetVersion(
            id=21,
            uuid='dataset-version-1',
            dataset_id=11,
            version_number=1,
            status=AnalyticsDatasetVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            grain_key=AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
            freshness_source_type=AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
            freshness_strategy=AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
        )

        dataset_repository = StubDatasetRepository([dataset])
        dataset_version_repository = StubDatasetVersionRepository([old_version])
        service = AnalyticsDatasetService(
            dataset_repository=dataset_repository,
            dataset_version_repository=dataset_version_repository,
        )

        new_version = service.create_dataset_version(
            dataset.id,
            {
                'grain_key': AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
                'source_contract_json': {'form_codes': ['FORM-A']},
                'query_spec_json': {'select': ['count(*)']},
                'transform_spec_json': {'steps': []},
                'freshness_source_type': AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
                'freshness_strategy': AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
            },
            actor=actor,
        )
        published_version = service.publish_dataset_version(new_version.id, actor=actor)

        assert new_version.version_number == 2
        assert published_version.status == AnalyticsDatasetVersion.STATUS_PUBLISHED
        assert published_version.is_current_published is True
        assert published_version.is_current_draft is False
        assert published_version.published_at is not None
        assert old_version.status == AnalyticsDatasetVersion.STATUS_ARCHIVED
        assert old_version.is_current_published is False
        assert dataset.status == AnalyticsDataset.STATUS_ACTIVE
        assert dataset.is_active is True
        assert dataset_version_repository.archived_calls == [
            {
                'dataset_id': dataset.id,
                'except_version_id': published_version.id,
            }
        ]


def test_start_and_complete_dataset_run_persists_preview_and_summary_payloads():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetRunService

        actor = SimpleNamespace(id=9, uuid='actor-uuid')
        dataset = AnalyticsDataset(
            id=11,
            uuid='dataset-uuid',
            dataset_key='submission-ringkas',
            name='Submission Ringkas',
            source_domain=AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
            source_type=AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
            status=AnalyticsDataset.STATUS_ACTIVE,
        )
        published_version = AnalyticsDatasetVersion(
            id=22,
            uuid='dataset-version-2',
            dataset_id=11,
            version_number=2,
            status=AnalyticsDatasetVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            grain_key=AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
            freshness_source_type=AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
            freshness_strategy=AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
        )

        service = AnalyticsDatasetRunService(
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([published_version]),
            dataset_run_repository=StubDatasetRunRepository(),
        )

        run = service.start_run(
            dataset.id,
            published_version.id,
            {
                'trigger_type': AnalyticsDatasetRun.TRIGGER_MANUAL,
                'requested_reporting_year': 2026,
                'requested_filters_json': {'scope_code': 'JBR'},
            },
            actor=actor,
        )

        assert run.status == AnalyticsDatasetRun.STATUS_RUNNING
        assert run.started_at is not None
        assert run.run_key

        completed_run = service.complete_run(
            run.id,
            {
                'result_row_count': 12,
                'result_schema_json': [{'key': 'total', 'type': 'integer'}],
                'result_preview_json': [{'total': 10}],
                'summary_json': {'freshness': 'ok'},
                'materialization_ref': 'mat-run-001',
            },
            actor=actor,
        )

        assert completed_run.status == AnalyticsDatasetRun.STATUS_SUCCEEDED
        assert completed_run.finished_at is not None
        assert completed_run.result_row_count == 12
        assert completed_run.result_schema_json == [{'key': 'total', 'type': 'integer'}]
        assert completed_run.result_preview_json == [{'total': 10}]
        assert completed_run.summary_json == {'freshness': 'ok'}
        assert completed_run.materialization_ref == 'mat-run-001'



def test_fail_dataset_run_persists_error_payload():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetRunService

        actor = SimpleNamespace(id=9, uuid='actor-uuid')
        dataset = AnalyticsDataset(
            id=11,
            uuid='dataset-uuid',
            dataset_key='submission-ringkas',
            name='Submission Ringkas',
            source_domain=AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
            source_type=AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
            status=AnalyticsDataset.STATUS_ACTIVE,
        )
        published_version = AnalyticsDatasetVersion(
            id=22,
            uuid='dataset-version-2',
            dataset_id=11,
            version_number=2,
            status=AnalyticsDatasetVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            grain_key=AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
            freshness_source_type=AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
            freshness_strategy=AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
        )

        service = AnalyticsDatasetRunService(
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([published_version]),
            dataset_run_repository=StubDatasetRunRepository(),
        )

        run = service.start_run(
            dataset.id,
            published_version.id,
            {'trigger_type': AnalyticsDatasetRun.TRIGGER_MANUAL},
            actor=actor,
        )
        failed_run = service.fail_run(
            run.id,
            {
                'error_code': 'QUERY_TIMEOUT',
                'error_message': 'Dataset execution timed out.',
                'error_detail_json': {'step': 'materialize'},
            },
            actor=actor,
        )

        assert failed_run.status == AnalyticsDatasetRun.STATUS_FAILED
        assert failed_run.finished_at is not None
        assert failed_run.error_code == 'QUERY_TIMEOUT'
        assert failed_run.error_message == 'Dataset execution timed out.'
        assert failed_run.error_detail_json == {'step': 'materialize'}



def test_start_run_rejects_unpublished_dataset_version():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetRunService

        dataset = AnalyticsDataset(
            id=11,
            uuid='dataset-uuid',
            dataset_key='submission-ringkas',
            name='Submission Ringkas',
            source_domain=AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
            source_type=AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
            status=AnalyticsDataset.STATUS_ACTIVE,
        )
        draft_version = AnalyticsDatasetVersion(
            id=23,
            uuid='dataset-version-3',
            dataset_id=11,
            version_number=3,
            status=AnalyticsDatasetVersion.STATUS_DRAFT,
            is_current_draft=True,
            is_current_published=False,
            grain_key=AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
            freshness_source_type=AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
            freshness_strategy=AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
        )

        service = AnalyticsDatasetRunService(
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([draft_version]),
            dataset_run_repository=StubDatasetRunRepository(),
        )

        try:
            service.start_run(
                dataset.id,
                draft_version.id,
                {'trigger_type': AnalyticsDatasetRun.TRIGGER_MANUAL},
            )
        except ValueError as exc:
            assert 'published' in str(exc)
        else:
            raise AssertionError('Expected ValueError for unpublished dataset version.')



def test_dataset_run_submission_source_filter_ignores_dataset_source_type_aliases():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetRunService

        service = AnalyticsDatasetRunService(dataset_run_repository=StubDatasetRunRepository())

        assert service._resolve_submission_source_type_filter(
            requested_filters={},
            source_contract={'source_type': 'submission_fact'},
            settings_json={'source_type': 'aggregated_submission_fact'},
        ) is None


def test_dataset_run_submission_source_filter_uses_explicit_ingestion_source_type():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetRunService

        service = AnalyticsDatasetRunService(dataset_run_repository=StubDatasetRunRepository())

        assert service._resolve_submission_source_type_filter(
            requested_filters={'submission_source_type': 'web-preview'},
            source_contract={'source_type': 'submission_fact'},
            settings_json={},
        ) == 'web-preview'



def test_execute_run_materializes_submission_rows_into_summary():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetRunService

        actor = SimpleNamespace(id=9, uuid='actor-uuid')
        dataset = AnalyticsDataset(
            id=11,
            uuid='dataset-uuid',
            dataset_key='analytics-harmonisasi-test',
            name='Analytics Harmonisasi Test',
            source_domain=AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
            source_type=AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
            primary_source_ref='FORM-HARMONISASI-TEST',
            status=AnalyticsDataset.STATUS_ACTIVE,
        )
        published_version = AnalyticsDatasetVersion(
            id=22,
            uuid='dataset-version-2',
            dataset_id=11,
            version_number=2,
            status=AnalyticsDatasetVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            source_contract_json={'form_code': 'FORM-HARMONISASI-TEST', 'source_type': 'harmonisasi_manual', 'reporting_year': 2026},
            transform_spec_json={'date_field': 'tanggal'},
            grain_key=AnalyticsDatasetVersion.GRAIN_PER_SUBMISSION,
            output_schema_json=[{'key': 'tanggal', 'type': 'date'}],
            freshness_source_type=AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
            freshness_strategy=AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
        )

        service = AnalyticsDatasetRunService(
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([published_version]),
            dataset_run_repository=StubDatasetRunRepository(),
        )

        def _fake_materialize_payload(run):
            rows = [{
                'tanggal': '2026-03-14',
                'reporting_year': 2026,
                'quarter_number': 1,
                'quarter_label': '2026-Q1',
                'semester_number': 1,
                'semester_label': '2026-S1',
                'year_label': '2026',
                'daerah': 'Kota Bandung',
                'jenis': 'Raperda',
                'hasil': 'Selesai',
                'tim_kerja': 'Tim A',
            }]
            summary = service._build_submission_summary(
                rows,
                run,
                dataset,
                published_version,
                {'form_codes': ['FORM-HARMONISASI-TEST'], 'latest_submitted_at': '2026-03-14T09:00:00+00:00'},
            )
            return {
                'freshness_status': AnalyticsDatasetRun.FRESHNESS_FRESH,
                'source_watermark': '2026-03-14T09:00:00+00:00',
                'source_snapshot_json': {'form_codes': ['FORM-HARMONISASI-TEST']},
                'result_row_count': 1,
                'result_schema_json': [{'key': 'tanggal', 'type': 'date'}],
                'result_preview_json': rows,
                'materialization_ref': 'analytics://dataset-runs/1',
                'summary_json': summary,
            }

        service._materialize_run_payload = _fake_materialize_payload

        run = service.execute_run(
            dataset.id,
            published_version.id,
            {
                'trigger_type': AnalyticsDatasetRun.TRIGGER_MANUAL,
                'requested_reporting_year': 2026,
                'requested_filters_json': {'source_type': 'harmonisasi_manual'},
            },
            actor=actor,
        )

        assert run.status == AnalyticsDatasetRun.STATUS_SUCCEEDED
        assert run.result_row_count == 1
        assert run.freshness_status == AnalyticsDatasetRun.FRESHNESS_FRESH
        assert run.summary_json['completion']['selesai'] == 1
        assert run.summary_json['filter_dimensions']['reporting_years'] == [2026]
        assert run.summary_json['row_snapshots'][0]['quarter_label'] == '2026-Q1'
        assert run.summary_json['row_snapshots'][0]['semester_label'] == '2026-S1'
        assert run.source_snapshot_json['form_codes'] == ['FORM-HARMONISASI-TEST']
