from decimal import Decimal
from types import SimpleNamespace

from app import create_app
from app.modules.analytics.models import (
    AnalyticsDataset,
    AnalyticsDatasetVersion,
    AnalyticsIndicatorDefinition,
    AnalyticsIndicatorProgressItem,
    AnalyticsIndicatorResult,
    AnalyticsIndicatorVersion,
    AnalyticsReportDefinition,
    AnalyticsReportVersion,
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


class StubReportDefinitionRepository(SaveMixin):
    def __init__(self, definitions=None):
        super().__init__()
        self.definitions = {item.id: item for item in (definitions or []) if getattr(item, 'id', None) is not None}

    def save(self, obj):
        obj = super().save(obj)
        self.definitions[obj.id] = obj
        return obj

    def get_by_id(self, report_definition_id):
        return self.definitions.get(report_definition_id)


class StubReportVersionRepository(SaveMixin):
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

    def get_next_version_number(self, report_definition_id):
        numbers = [
            version.version_number
            for version in self.versions
            if version.report_definition_id == report_definition_id
        ]
        return (max(numbers) if numbers else 0) + 1

    def get_draft_version(self, report_definition_id):
        for version in self.versions:
            if version.report_definition_id == report_definition_id and getattr(version, 'is_current_draft', False):
                return version
        return None

    def archive_published_others(self, report_definition_id, except_version_id=None):
        self.archived_calls.append(
            {
                'report_definition_id': report_definition_id,
                'except_version_id': except_version_id,
            }
        )
        archived = []
        for version in self.versions:
            if version.report_definition_id != report_definition_id:
                continue
            if except_version_id is not None and version.id == except_version_id:
                continue
            if version.is_current_published:
                version.is_current_published = False
                version.is_current_draft = False
                version.status = AnalyticsReportVersion.STATUS_ARCHIVED
                archived.append(version)
        return archived


class StubIndicatorDefinitionRepository(SaveMixin):
    def __init__(self, definitions=None):
        super().__init__()
        self.definitions = {item.id: item for item in (definitions or []) if getattr(item, 'id', None) is not None}

    def save(self, obj):
        obj = super().save(obj)
        self.definitions[obj.id] = obj
        return obj

    def get_by_id(self, indicator_definition_id):
        return self.definitions.get(indicator_definition_id)


class StubIndicatorVersionRepository(SaveMixin):
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

    def get_next_version_number(self, indicator_definition_id):
        numbers = [
            version.version_number
            for version in self.versions
            if version.indicator_definition_id == indicator_definition_id
        ]
        return (max(numbers) if numbers else 0) + 1

    def archive_published_others(self, indicator_definition_id, except_version_id=None):
        self.archived_calls.append(
            {
                'indicator_definition_id': indicator_definition_id,
                'except_version_id': except_version_id,
            }
        )
        archived = []
        for version in self.versions:
            if version.indicator_definition_id != indicator_definition_id:
                continue
            if except_version_id is not None and version.id == except_version_id:
                continue
            if version.is_current_published:
                version.is_current_published = False
                version.is_current_draft = False
                version.status = AnalyticsIndicatorVersion.STATUS_ARCHIVED
                archived.append(version)
        return archived


class StubReportVersionIndicatorRepository(SaveMixin):
    pass


class StubDatasetRepository:
    def __init__(self, datasets=None):
        self.datasets = {item.id: item for item in (datasets or []) if getattr(item, 'id', None) is not None}

    def get_all(self):
        return list(self.datasets.values())

    def get_by_id(self, dataset_id):
        return self.datasets.get(dataset_id)


class StubDatasetVersionRepository:
    def __init__(self, versions=None):
        self.versions = {item.id: item for item in (versions or []) if getattr(item, 'id', None) is not None}

    def get_by_id(self, version_id):
        return self.versions.get(version_id)

    def get_published_version(self, dataset_id):
        for version in self.versions.values():
            if getattr(version, 'dataset_id', None) == dataset_id and getattr(version, 'is_current_published', False):
                return version
        return None

    def get_draft_version(self, dataset_id):
        for version in self.versions.values():
            if getattr(version, 'dataset_id', None) == dataset_id and getattr(version, 'is_current_draft', False):
                return version
        return None


class StubDatasetRunRepository:
    def __init__(self, runs_by_version=None):
        self.runs_by_version = runs_by_version or {}

    def get_latest_for_dataset_version(self, dataset_version_id):
        return self.runs_by_version.get(dataset_version_id)


class StubResultRepository(SaveMixin):
    def __init__(self, results=None):
        super().__init__()
        self.results = []
        for result in results or []:
            self.save(result)

    def save(self, obj):
        obj = super().save(obj)
        if obj not in self.results:
            self.results.append(obj)
        return obj

    def get_latest_for_period(self, indicator_version_id, reporting_year=None, reporting_period_id=None):
        candidates = [
            result
            for result in self.results
            if result.indicator_version_id == indicator_version_id
            and result.reporting_year == reporting_year
            and result.reporting_period_id == reporting_period_id
        ]
        if not candidates:
            return None
        return candidates[-1]


class StubProgressEntryRepository(SaveMixin):
    def __init__(self, entries=None):
        super().__init__()
        self.entries = []
        self.next_item_id = 1
        for entry in entries or []:
            self.save(entry)

    def save(self, obj):
        obj = super().save(obj)
        if obj not in self.entries:
            self.entries.append(obj)
        for item in getattr(obj, 'items', []) or []:
            if getattr(item, 'id', None) is None:
                item.id = self.next_item_id
                self.next_item_id += 1
            item.progress_entry_id = obj.id
        return obj

    def get_by_id(self, progress_entry_id):
        for entry in self.entries:
            if entry.id == progress_entry_id:
                return entry
        return None


def test_query_service_list_datasets_falls_back_to_published_run_when_draft_has_no_run():
    from app.modules.analytics.services import AnalyticsQueryService

    dataset = SimpleNamespace(id=4, dataset_key='harmon-2026', name='Harmonisasi 2026')
    draft_version = SimpleNamespace(id=8, dataset_id=4, is_current_draft=True, is_current_published=False)
    published_version = SimpleNamespace(id=7, dataset_id=4, is_current_draft=False, is_current_published=True)
    published_run = SimpleNamespace(id=15, dataset_version_id=7, status='succeeded', result_row_count=104)

    service = AnalyticsQueryService(
        report_definition_repository=StubReportDefinitionRepository([]),
        report_version_repository=StubReportVersionRepository([]),
        indicator_definition_repository=StubIndicatorDefinitionRepository([]),
        indicator_version_repository=StubIndicatorVersionRepository([]),
        report_version_indicator_repository=StubReportVersionIndicatorRepository(),
        result_repository=StubResultRepository([]),
        progress_entry_repository=StubProgressEntryRepository([]),
        dataset_repository=StubDatasetRepository([dataset]),
        dataset_version_repository=StubDatasetVersionRepository([draft_version, published_version]),
        dataset_run_repository=StubDatasetRunRepository({7: published_run}),
    )

    items = service.list_datasets()

    assert items[0]['draft_version'] == draft_version
    assert items[0]['published_version'] == published_version
    assert items[0]['latest_run'] == published_run


def test_create_dataset_bundle_rejects_invalid_contract_without_persisting_dataset():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsDatasetService

        class RecordingDatasetRepository(SaveMixin):
            def __init__(self):
                super().__init__()
                self.datasets = []

            def save(self, obj):
                obj = super().save(obj)
                if obj not in self.datasets:
                    self.datasets.append(obj)
                return obj

            def get_by_id(self, dataset_id):
                for dataset in self.datasets:
                    if dataset.id == dataset_id:
                        return dataset
                return None

            def get_by_key(self, dataset_key):
                for dataset in self.datasets:
                    if dataset.dataset_key == dataset_key:
                        return dataset
                return None

        class RecordingDatasetVersionRepository(SaveMixin):
            def __init__(self):
                super().__init__()
                self.versions = []

            def save(self, obj):
                obj = super().save(obj)
                if obj not in self.versions:
                    self.versions.append(obj)
                return obj

            def get_next_version_number(self, dataset_id):
                return 1

            def get_draft_version(self, dataset_id):
                return None

        dataset_repository = RecordingDatasetRepository()
        version_repository = RecordingDatasetVersionRepository()
        service = AnalyticsDatasetService(
            dataset_repository=dataset_repository,
            dataset_version_repository=version_repository,
        )

        payload = {
            'dataset': {
                'dataset_key': 'harmon-26',
                'name': 'Dataset Harmon 2026',
                'source_domain': AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
                'source_type': AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
            },
            'draft_version': {
                'source_contract_json': {'selected_fields': ['nama_indikator']},
                'output_schema_json': [],
                'dimension_definitions_json': [{'key': 'nama_indikator', 'label': 'Nama Indikator'}],
                'metric_definitions_json': [],
                'grain_key': AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
            },
        }

        try:
            service.create_dataset_bundle(payload)
            assert False, 'create_dataset_bundle seharusnya menolak draft tanpa metric definitions'
        except ValueError as exc:
            assert 'metric_definitions_json minimal satu metric' in str(exc)

        assert dataset_repository.datasets == []
        assert version_repository.versions == []
        assert dataset_repository.get_by_key('harmon-26') is None


def test_create_publish_indicator_and_report_flow_archives_previous_versions():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsIndicatorService, AnalyticsReportService

        actor = SimpleNamespace(id=7, uuid='actor-uuid')

        report_definition = AnalyticsReportDefinition(
            id=21,
            uuid='report-def-uuid',
            report_key='pk-kanwil',
            dataset_id=7,
            name='PK Kanwil',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        old_report_version = AnalyticsReportVersion(
            id=31,
            uuid='report-version-uuid-1',
            report_definition_id=21,
            dataset_version_id=701,
            version_number=1,
            status=AnalyticsReportVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            title='PK 2025',
        )
        dataset = SimpleNamespace(id=7, dataset_key='dataset-pk', name='Dataset PK', settings_json={})
        dataset_version = SimpleNamespace(
            id=701,
            dataset_id=7,
            version_number=5,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[],
            dimension_definitions_json=[],
            metric_definitions_json=[],
        )
        report_definition_repository = StubReportDefinitionRepository([report_definition])
        report_version_repository = StubReportVersionRepository([old_report_version])
        dataset_repository = StubDatasetRepository([dataset])
        dataset_version_repository = StubDatasetVersionRepository([dataset_version])
        report_service = AnalyticsReportService(
            report_definition_repository=report_definition_repository,
            report_version_repository=report_version_repository,
            dataset_repository=dataset_repository,
            dataset_version_repository=dataset_version_repository,
        )

        indicator_definition = AnalyticsIndicatorDefinition(
            id=41,
            uuid='indicator-def-uuid',
            indicator_key='renaksi.tindak_lanjut',
            name='Tindak lanjut Renaksi',
            source_mode=AnalyticsIndicatorDefinition.SOURCE_MODE_MANUAL_INPUT,
            calculation_type=AnalyticsIndicatorDefinition.CALCULATION_CHECKLIST_COMPLETION,
            status=AnalyticsIndicatorDefinition.STATUS_DRAFT,
        )
        old_indicator_version = AnalyticsIndicatorVersion(
            id=51,
            uuid='indicator-version-uuid-1',
            indicator_definition_id=41,
            version_number=1,
            status=AnalyticsIndicatorVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            period_mode=AnalyticsIndicatorVersion.PERIOD_MODE_YEARLY,
            aggregation_strategy=AnalyticsIndicatorVersion.AGGREGATION_LAST_VALUE,
            meta_description='Versi indikator lama',
        )
        indicator_definition_repository = StubIndicatorDefinitionRepository([indicator_definition])
        indicator_version_repository = StubIndicatorVersionRepository([old_indicator_version])
        report_indicator_repository = StubReportVersionIndicatorRepository()
        indicator_service = AnalyticsIndicatorService(
            indicator_definition_repository=indicator_definition_repository,
            indicator_version_repository=indicator_version_repository,
            report_version_indicator_repository=report_indicator_repository,
        )

        new_report_version = report_service.create_report_version(
            21,
            {
                'title': 'PK 2026',
                'meta_description': 'Versi report terbaru untuk tahun aktif.',
                'narrative_guidance_json': {'summary_prompt': 'Ringkas capaian per indikator.'},
            },
            actor=actor,
        )
        new_indicator_version = indicator_service.create_indicator_version(
            41,
            {
                'status': AnalyticsIndicatorVersion.STATUS_DRAFT,
                'period_mode': AnalyticsIndicatorVersion.PERIOD_MODE_YEARLY,
                'aggregation_strategy': AnalyticsIndicatorVersion.AGGREGATION_LAST_VALUE,
                'meta_description': 'Narasi indikator wajib menjelaskan capaian dan hambatan.',
                'target_config_json': {'target_value': 100},
                'narrative_guidance_json': {'focus': ['capaian', 'kendala']},
            },
            actor=actor,
        )
        published_indicator = indicator_service.publish_indicator_version(new_indicator_version.id, actor=actor)
        mapping = indicator_service.attach_indicator_to_report_version(
            new_report_version.id,
            published_indicator.id,
            {
                'item_order': 1,
                'display_label': 'Tindak lanjut',
                'section_key': 'renaksi',
            },
            actor=actor,
        )
        published_report = report_service.publish_report_version(new_report_version.id, actor=actor)

        assert old_indicator_version.status == AnalyticsIndicatorVersion.STATUS_ARCHIVED
        assert old_indicator_version.is_current_published is False
        assert published_indicator.status == AnalyticsIndicatorVersion.STATUS_PUBLISHED
        assert published_indicator.is_current_published is True
        assert published_indicator.is_current_draft is False
        assert published_indicator.meta_description == 'Narasi indikator wajib menjelaskan capaian dan hambatan.'
        assert indicator_definition.status == AnalyticsIndicatorDefinition.STATUS_ACTIVE
        assert indicator_definition_repository.saved[-1] is indicator_definition

        assert mapping.report_version_id == new_report_version.id
        assert mapping.indicator_version_id == published_indicator.id
        assert mapping.display_label == 'Tindak lanjut'

        assert old_report_version.status == AnalyticsReportVersion.STATUS_ARCHIVED
        assert old_report_version.is_current_published is False
        assert published_report.status == AnalyticsReportVersion.STATUS_PUBLISHED
        assert published_report.is_current_published is True
        assert published_report.is_current_draft is False
        assert report_definition.status == AnalyticsReportDefinition.STATUS_ACTIVE
        assert report_definition_repository.saved[-1] is report_definition



def test_create_report_version_normalizes_block_configs_and_curated_dataset_contract():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        report_definition = AnalyticsReportDefinition(
            id=21,
            uuid='report-def-uuid',
            report_key='pk-kanwil',
            dataset_id=7,
            name='PK Kanwil',
            category_key='pk',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        dataset = SimpleNamespace(id=7, dataset_key='dataset-pk', name='Dataset PK', settings_json={})
        dataset_version = SimpleNamespace(
            id=701,
            dataset_id=7,
            version_number=5,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[
                {'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'},
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
                {'key': 'capaian_total', 'label': 'Capaian Total', 'type': 'integer'},
                {'key': 'achievement_pct', 'label': 'Achievement %', 'type': 'number'},
                {'key': 'latitude', 'label': 'Latitude', 'type': 'number'},
                {'key': 'longitude', 'label': 'Longitude', 'type': 'number'},
            ],
            dimension_definitions_json=[
                {'key': 'nama_bidang', 'label': 'Nama Bidang', 'type': 'string'},
            ],
            metric_definitions_json=[
                {'key': 'capaian_total', 'label': 'Capaian Total', 'type': 'integer'},
                {'key': 'achievement_pct', 'label': 'Achievement %', 'type': 'number'},
            ],
        )
        report_definition_repository = StubReportDefinitionRepository([report_definition])
        report_version_repository = StubReportVersionRepository()
        dataset_repository = StubDatasetRepository([dataset])
        dataset_version_repository = StubDatasetVersionRepository([dataset_version])
        report_service = AnalyticsReportService(
            report_definition_repository=report_definition_repository,
            report_version_repository=report_version_repository,
            dataset_repository=dataset_repository,
            dataset_version_repository=dataset_version_repository,
        )

        created_version = report_service.create_report_version(
            21,
            {
                'dataset_version_id': 701,
                'title': 'PK Kanwil 2026',
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Ringkasan KPI'},
                    {'type': 'plotly_timeseries', 'title': 'Tren PK'},
                    {'type': 'detail_table', 'title': 'Tabel PK'},
                    {'type': 'geo_map', 'title': 'Sebaran PK'},
                    {'type': 'narrative', 'title': 'Narasi PK', 'config': {'focus_field_keys': ['achievement_pct']}},
                ],
            },
        )

        dataset_contract = created_version.structure_json['dataset_contract']
        curated_fields = dataset_contract['curated_fields']
        curated_field_keys = [field['key'] for field in curated_fields]
        run_binding = dataset_contract['run_binding']
        blocks = created_version.structure_json['blocks']
        metric_block = next(block for block in blocks if block['type'] == 'metric_cards')
        chart_block = next(block for block in blocks if block['type'] == 'plotly_timeseries')
        table_block = next(block for block in blocks if block['type'] == 'detail_table')
        map_block = next(block for block in blocks if block['type'] == 'geo_map')
        narrative_block = next(block for block in blocks if block['type'] == 'narrative')

        assert dataset_contract['dataset_id'] == 7
        assert dataset_contract['dataset_version_id'] == 701
        assert dataset_contract['dataset_version_number'] == 5
        assert dataset_contract['grain_key'] == 'per_scope_per_year'
        assert 'tanggal' in curated_field_keys
        assert 'nama_indikator' in curated_field_keys
        assert 'capaian_total' in curated_field_keys
        assert 'achievement_pct' in curated_field_keys
        assert 'latitude' in curated_field_keys
        assert 'longitude' in curated_field_keys
        assert run_binding == {
            'dataset_id': 7,
            'dataset_key': 'dataset-pk',
            'dataset_version_id': 701,
            'dataset_version_number': 5,
            'report_title': 'PK Kanwil',
            'report_category_key': 'pk',
            'selection_mode': 'latest_succeeded_run',
        }
        assert metric_block['config']['metric_keys'] == ['capaian_total', 'achievement_pct']
        assert chart_block['config']['x_key'] == 'tanggal'
        assert chart_block['config']['series'][0]['key'] == 'capaian_total'
        assert table_block['config']['column_keys'] == ['tanggal', 'nama_indikator', 'capaian_total', 'achievement_pct', 'nama_bidang']
        assert map_block['config']['latitude_field'] == 'latitude'
        assert map_block['config']['longitude_field'] == 'longitude'
        assert narrative_block['config']['focus_field_keys'] == ['achievement_pct']



def test_update_report_version_preserves_explicitly_empty_blocks():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        report_definition = AnalyticsReportDefinition(
            id=23,
            uuid='report-def-uuid-empty-blocks',
            report_key='empty-block-test',
            dataset_id=9,
            name='Report Kosong Sementara',
            category_key='custom',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        dataset = SimpleNamespace(id=9, dataset_key='dataset-empty-blocks', name='Dataset Empty Blocks', settings_json={})
        dataset_version = SimpleNamespace(
            id=703,
            dataset_id=9,
            version_number=1,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[{'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'}],
            dimension_definitions_json=[],
            metric_definitions_json=[{'key': 'jumlah_dokumen', 'label': 'Jumlah Dokumen', 'type': 'integer'}],
        )
        existing_draft = AnalyticsReportVersion(
            id=33,
            uuid='report-version-empty-blocks',
            report_definition_id=23,
            dataset_version_id=703,
            version_number=1,
            status=AnalyticsReportVersion.STATUS_DRAFT,
            is_current_draft=True,
            is_current_published=False,
            title='Draft yang sebelumnya punya block',
            structure_json={
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Block lama', 'config': {'metric_keys': ['jumlah_dokumen']}},
                ],
            },
        )
        report_service = AnalyticsReportService(
            report_definition_repository=StubReportDefinitionRepository([report_definition]),
            report_version_repository=StubReportVersionRepository([existing_draft]),
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([dataset_version]),
        )

        updated_version = report_service.upsert_draft_version(
            23,
            {
                'dataset_version_id': 703,
                'title': 'Draft tanpa block',
                'blocks': [],
            },
        )

        assert updated_version.structure_json['blocks'] == []


def test_report_builder_preserves_multi_dataset_sources_and_block_aliases():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        report_definition = AnalyticsReportDefinition(
            id=24,
            uuid='report-def-multi-source',
            report_key='pk-renaksi-multi-source',
            dataset_id=None,
            name='PK dan Renaksi Multi Dataset',
            category_key='pk',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
            settings_json={'report_family': 'pk'},
        )
        pk_dataset = SimpleNamespace(id=11, dataset_key='dataset-pk', name='Dataset PK', settings_json={})
        renaksi_dataset = SimpleNamespace(id=12, dataset_key='dataset-renaksi', name='Dataset Renaksi', settings_json={})
        pk_version = SimpleNamespace(
            id=801,
            dataset_id=11,
            version_number=3,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
                {'key': 'target_kinerja', 'label': 'Target Kinerja', 'type': 'number'},
                {'key': 'nilai_realisasi', 'label': 'Nilai Realisasi', 'type': 'number'},
            ],
            dimension_definitions_json=[{'key': 'nama_indikator', 'label': 'Nama Indikator'}],
            metric_definitions_json=[
                {'key': 'target_kinerja', 'label': 'Target Kinerja', 'type': 'number'},
                {'key': 'nilai_realisasi', 'label': 'Nilai Realisasi', 'type': 'number'},
            ],
        )
        renaksi_version = SimpleNamespace(
            id=802,
            dataset_id=12,
            version_number=2,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_action_per_period',
            output_schema_json=[
                {'key': 'kegiatan', 'label': 'Kegiatan', 'type': 'string'},
                {'key': 'status', 'label': 'Status', 'type': 'string'},
                {'key': 'progress_pct', 'label': 'Progress', 'type': 'number'},
            ],
            dimension_definitions_json=[
                {'key': 'kegiatan', 'label': 'Kegiatan'},
                {'key': 'status', 'label': 'Status'},
            ],
            metric_definitions_json=[{'key': 'progress_pct', 'label': 'Progress', 'type': 'number'}],
        )
        report_service = AnalyticsReportService(
            report_definition_repository=StubReportDefinitionRepository([report_definition]),
            report_version_repository=StubReportVersionRepository(),
            dataset_repository=StubDatasetRepository([pk_dataset, renaksi_dataset]),
            dataset_version_repository=StubDatasetVersionRepository([pk_version, renaksi_version]),
        )

        created_version = report_service.create_report_version(
            24,
            {
                'title': 'PK + Renaksi 2026',
                'data_sources': [
                    {'alias': 'pk_target', 'dataset_id': 11, 'dataset_version_id': 801},
                    {'alias': 'renaksi_progress', 'dataset_id': 12, 'dataset_version_id': 802},
                ],
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Ringkasan PK', 'data_source_alias': 'pk_target'},
                    {'type': 'detail_table', 'title': 'Progress Renaksi', 'data_source_alias': 'renaksi_progress'},
                ],
            },
        )

        structure = created_version.structure_json
        assert created_version.dataset_version_id is None
        assert structure['data_sources'][0]['alias'] == 'pk_target'
        assert structure['data_sources'][0]['dataset_key'] == 'dataset-pk'
        assert structure['data_sources'][0]['curated_fields'][1]['key'] == 'target_kinerja'
        assert structure['data_sources'][1]['alias'] == 'renaksi_progress'
        assert structure['data_sources'][1]['dataset_key'] == 'dataset-renaksi'
        assert structure['blocks'][0]['data_source_alias'] == 'pk_target'
        assert structure['blocks'][0]['config']['metric_keys'] == ['target_kinerja', 'nilai_realisasi']
        assert structure['blocks'][1]['data_source_alias'] == 'renaksi_progress'
        assert structure['blocks'][1]['config']['column_keys'] == ['kegiatan', 'progress_pct', 'status']



def test_report_builder_publishes_report_version_with_multi_dataset_sources_without_primary_dataset_version():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        report_definition = AnalyticsReportDefinition(
            id=25,
            uuid='report-def-publish-multi-source',
            report_key='pk-renaksi-publish',
            dataset_id=None,
            name='PK Renaksi Publish',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        report_version = AnalyticsReportVersion(
            id=88,
            uuid='report-version-publish-multi-source',
            report_definition_id=25,
            dataset_version_id=None,
            version_number=1,
            status=AnalyticsReportVersion.STATUS_DRAFT,
            is_current_draft=True,
            is_current_published=False,
            title='PK Renaksi Multi Source',
            structure_json={
                'data_sources': [
                    {'alias': 'pk_target', 'dataset_id': 11, 'dataset_version_id': 801},
                    {'alias': 'renaksi_progress', 'dataset_id': 12, 'dataset_version_id': 802},
                ],
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Ringkasan PK', 'data_source_alias': 'pk_target', 'config': {}},
                ],
            },
        )
        report_service = AnalyticsReportService(
            report_definition_repository=StubReportDefinitionRepository([report_definition]),
            report_version_repository=StubReportVersionRepository([report_version]),
            dataset_repository=StubDatasetRepository(),
            dataset_version_repository=StubDatasetVersionRepository(),
        )

        published = report_service.publish_report_version(88)

        assert published.status == AnalyticsReportVersion.STATUS_PUBLISHED
        assert published.is_current_published is True
        assert published.is_current_draft is False


def test_report_builder_derives_publishable_data_sources_from_report_items():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        report_definition = AnalyticsReportDefinition(
            id=26,
            uuid='report-def-item-sources',
            report_key='item-source-report',
            dataset_id=None,
            name='Report Item Source',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        dataset = SimpleNamespace(id=13, dataset_key='dataset-item-source', name='Dataset Item Source', settings_json={})
        dataset_version = SimpleNamespace(
            id=803,
            dataset_id=13,
            version_number=1,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[{'key': 'status_realisasi', 'label': 'Status Realisasi', 'type': 'string'}],
            dimension_definitions_json=[{'key': 'status_realisasi', 'label': 'Status Realisasi'}],
            metric_definitions_json=[],
        )
        report_service = AnalyticsReportService(
            report_definition_repository=StubReportDefinitionRepository([report_definition]),
            report_version_repository=StubReportVersionRepository(),
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([dataset_version]),
        )

        draft = report_service.create_report_version(
            26,
            {
                'title': 'Draft item source',
                'data_sources': [],
                'report_items': [
                    {
                        'item_key': 'indikator-1',
                        'name': 'Indikator 1',
                        'datasets': [
                            {
                                'source_mode': 'dataset_driven',
                                'dataset_id': 13,
                                'dataset_version_id': '',
                                'actual_metric_key': 'status_realisasi',
                                'aggregation_mode': 'count_value',
                            }
                        ],
                    }
                ],
                'blocks': [],
            },
        )
        published = report_service.publish_report_version(draft.id)

        assert draft.dataset_version_id is None
        assert draft.structure_json['data_sources'][0]['dataset_id'] == 13
        assert draft.structure_json['data_sources'][0]['dataset_version_id'] == 803
        assert draft.structure_json['data_sources'][0]['alias'] == 'indikator_1_1'
        assert published.status == AnalyticsReportVersion.STATUS_PUBLISHED



def test_report_builder_keeps_metric_role_when_output_schema_declares_numeric_business_fields_first():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        report_definition = AnalyticsReportDefinition(
            id=22,
            uuid='report-def-uuid-business-metric',
            report_key='ik-kanwil',
            dataset_id=8,
            name='IK Kanwil',
            category_key='ik',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        dataset = SimpleNamespace(id=8, dataset_key='dataset-ik', name='Dataset IK', settings_json={})
        dataset_version = SimpleNamespace(
            id=702,
            dataset_id=8,
            version_number=1,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[
                {'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'},
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
                {'key': 'target_kinerja', 'label': 'Target Kinerja', 'type': 'number'},
                {'key': 'nilai_realisasi', 'label': 'Nilai Realisasi', 'type': 'number'},
            ],
            dimension_definitions_json=[
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
            ],
            metric_definitions_json=[
                {'key': 'target_kinerja', 'label': 'Target Kinerja', 'type': 'number'},
                {'key': 'nilai_realisasi', 'label': 'Nilai Realisasi', 'type': 'number'},
            ],
        )
        report_service = AnalyticsReportService(
            report_definition_repository=StubReportDefinitionRepository([report_definition]),
            report_version_repository=StubReportVersionRepository(),
            dataset_repository=StubDatasetRepository([dataset]),
            dataset_version_repository=StubDatasetVersionRepository([dataset_version]),
        )

        created_version = report_service.create_report_version(
            22,
            {
                'dataset_version_id': 702,
                'title': 'IK Kanwil 2026',
                'blocks': [
                    {'type': 'metric_cards', 'title': 'Ringkasan IK'},
                    {'type': 'plotly_timeseries', 'title': 'Tren IK'},
                ],
            },
        )

        curated_roles = {
            field['key']: field['role']
            for field in created_version.structure_json['dataset_contract']['curated_fields']
        }
        metric_block = next(block for block in created_version.structure_json['blocks'] if block['type'] == 'metric_cards')
        chart_block = next(block for block in created_version.structure_json['blocks'] if block['type'] == 'plotly_timeseries')

        assert curated_roles['target_kinerja'] == 'metric'
        assert curated_roles['nilai_realisasi'] == 'metric'
        assert metric_block['config']['metric_keys'] == ['target_kinerja', 'nilai_realisasi']
        assert [series['key'] for series in chart_block['config']['series']] == ['target_kinerja', 'nilai_realisasi']



def test_record_progress_entry_with_items_and_sync_result_updates_narrative_without_losing_dataset_trace():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsIndicatorResultService

        existing_result = AnalyticsIndicatorResult(
            id=61,
            uuid='result-uuid-1',
            indicator_version_id=51,
            dataset_run_id=701,
            reporting_year=2026,
            reporting_period_id=3,
            measured_value=Decimal('8.5000'),
            target_value=Decimal('10.0000'),
            completion_status=AnalyticsIndicatorResult.COMPLETION_NOT_STARTED,
            source_snapshot_json={
                'dataset_run_id': 701,
                'dataset_id': 99,
                'dataset_version_id': 199,
                'source_mode': 'dataset_driven',
            },
        )
        result_repository = StubResultRepository([existing_result])
        progress_repository = StubProgressEntryRepository()
        service = AnalyticsIndicatorResultService(
            result_repository=result_repository,
            progress_entry_repository=progress_repository,
        )
        actor = SimpleNamespace(id=9, uuid='reviewer-uuid')

        progress_entry = service.record_progress_entry(
            {
                'indicator_version_id': 51,
                'reporting_year': 2026,
                'reporting_period_id': 3,
                'status': 'completed',
                'progress_percent': Decimal('85.0000'),
                'qualitative_summary': 'Sebagian besar target tercapai melalui percepatan tindak lanjut.',
                'constraint_notes': 'Masih ada hambatan koordinasi lintas unit.',
                'narrative_context_json': {
                    'highlights': ['koordinasi meningkat'],
                    'risks': ['keterlambatan verifikasi'],
                },
                'summary_json': {'completed_items': 2, 'total_items': 3},
                'items': [
                    {
                        'item_order': 1,
                        'status': AnalyticsIndicatorProgressItem.STATUS_DONE,
                        'title': 'Konsolidasi data',
                        'description': 'Konsolidasi data capaian indikator.',
                    },
                    {
                        'item_order': 2,
                        'status': AnalyticsIndicatorProgressItem.STATUS_BLOCKED,
                        'title': 'Validasi lintas unit',
                        'description': 'Menunggu klarifikasi final.',
                    },
                ],
            },
            actor=actor,
        )
        synced_result = service.sync_result_from_progress(progress_entry.id, actor=actor)

        assert len(progress_entry.items) == 2
        assert progress_entry.items[0].progress_entry_id == progress_entry.id
        assert progress_entry.items[0].title == 'Konsolidasi data'
        assert progress_entry.items[1].status == AnalyticsIndicatorProgressItem.STATUS_BLOCKED

        assert synced_result.id == 61
        assert synced_result.dataset_run_id == 701
        assert synced_result.measured_value == Decimal('8.5000')
        assert synced_result.target_value == Decimal('10.0000')
        assert synced_result.completion_status == AnalyticsIndicatorResult.COMPLETION_COMPLETED
        assert synced_result.qualitative_summary == 'Sebagian besar target tercapai melalui percepatan tindak lanjut.'
        assert synced_result.constraint_notes == 'Masih ada hambatan koordinasi lintas unit.'
        assert synced_result.narrative_context_json == {
            'highlights': ['koordinasi meningkat'],
            'risks': ['keterlambatan verifikasi'],
        }
        assert synced_result.source_snapshot_json['dataset_run_id'] == 701



def test_attach_indicator_to_report_version_rejects_unpublished_indicator_version():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsIndicatorService

        indicator_definition_repository = StubIndicatorDefinitionRepository()
        unpublished_indicator_version = AnalyticsIndicatorVersion(
            id=151,
            uuid='indicator-version-uuid-151',
            indicator_definition_id=41,
            version_number=2,
            status=AnalyticsIndicatorVersion.STATUS_DRAFT,
            is_current_draft=True,
            is_current_published=False,
            period_mode=AnalyticsIndicatorVersion.PERIOD_MODE_YEARLY,
            aggregation_strategy=AnalyticsIndicatorVersion.AGGREGATION_SUM,
        )
        indicator_version_repository = StubIndicatorVersionRepository([unpublished_indicator_version])
        report_indicator_repository = StubReportVersionIndicatorRepository()
        service = AnalyticsIndicatorService(
            indicator_definition_repository=indicator_definition_repository,
            indicator_version_repository=indicator_version_repository,
            report_version_indicator_repository=report_indicator_repository,
        )

        try:
            service.attach_indicator_to_report_version(
                report_version_id=31,
                indicator_version_id=151,
                data={'item_order': 1},
            )
            assert False, 'Expected ValueError when attaching unpublished indicator version'
        except ValueError as error:
            assert str(error) == 'Hanya indicator version published yang boleh di-attach ke report version.'

        assert report_indicator_repository.saved == []



def test_create_indicator_version_rejects_dataset_manual_source_mode_mismatch():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsIndicatorService

        manual_indicator_definition = AnalyticsIndicatorDefinition(
            id=241,
            uuid='indicator-def-uuid-241',
            indicator_key='renaksi.manual',
            name='Renaksi Manual',
            source_mode=AnalyticsIndicatorDefinition.SOURCE_MODE_MANUAL_INPUT,
            calculation_type=AnalyticsIndicatorDefinition.CALCULATION_CHECKLIST_COMPLETION,
            status=AnalyticsIndicatorDefinition.STATUS_ACTIVE,
        )
        indicator_definition_repository = StubIndicatorDefinitionRepository([manual_indicator_definition])
        indicator_version_repository = StubIndicatorVersionRepository()
        report_indicator_repository = StubReportVersionIndicatorRepository()
        service = AnalyticsIndicatorService(
            indicator_definition_repository=indicator_definition_repository,
            indicator_version_repository=indicator_version_repository,
            report_version_indicator_repository=report_indicator_repository,
        )

        try:
            service.create_indicator_version(
                241,
                {
                    'dataset_id': 77,
                    'dataset_version_id': 78,
                    'period_mode': AnalyticsIndicatorVersion.PERIOD_MODE_YEARLY,
                },
            )
            assert False, 'Expected ValueError for manual_input indicator using dataset linkage'
        except ValueError as error:
            assert str(error) == 'Indicator manual_input tidak boleh membawa dataset_id atau dataset_version_id.'

        assert indicator_version_repository.saved == []



def test_record_result_for_dataset_driven_indicator_builds_default_source_trace():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsIndicatorResultService

        indicator_version = AnalyticsIndicatorVersion(
            id=88,
            uuid='indicator-version-uuid-88',
            indicator_definition_id=41,
            dataset_id=77,
            dataset_version_id=78,
            status=AnalyticsIndicatorVersion.STATUS_PUBLISHED,
            is_current_published=True,
            period_mode=AnalyticsIndicatorVersion.PERIOD_MODE_YEARLY,
            aggregation_strategy=AnalyticsIndicatorVersion.AGGREGATION_SUM,
        )
        indicator_version.definition = AnalyticsIndicatorDefinition(
            id=41,
            uuid='indicator-def-uuid-41',
            indicator_key='indikator.dataset',
            source_mode=AnalyticsIndicatorDefinition.SOURCE_MODE_DATASET_DRIVEN,
            calculation_type=AnalyticsIndicatorDefinition.CALCULATION_ABSOLUTE_COUNT,
            name='Indikator Dataset',
            status=AnalyticsIndicatorDefinition.STATUS_ACTIVE,
        )

        result_repository = StubResultRepository()
        progress_repository = StubProgressEntryRepository()
        indicator_version_repository = StubIndicatorVersionRepository([indicator_version])
        service = AnalyticsIndicatorResultService(
            result_repository=result_repository,
            progress_entry_repository=progress_repository,
            indicator_version_repository=indicator_version_repository,
        )

        result = service.record_result(
            {
                'indicator_version_id': 88,
                'dataset_run_id': 900,
                'reporting_year': 2026,
                'reporting_period_id': 12,
                'measured_value': Decimal('42.0000'),
                'target_value': Decimal('50.0000'),
            }
        )

        assert result.dataset_run_id == 900
        assert result.measured_value == Decimal('42.0000')
        assert result.target_value == Decimal('50.0000')
        assert result.source_snapshot_json == {
            'source_mode': 'dataset_driven',
            'dataset_id': 77,
            'dataset_version_id': 78,
            'dataset_run_id': 900,
            'indicator_version_id': 88,
        }


def test_report_service_normalizes_legacy_report_type_alias_and_family_defaults():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsReportService

        dataset = SimpleNamespace(
            id=7,
            dataset_key='dataset-pk',
            name='Dataset PK',
            settings_json={},
        )
        dataset_version = SimpleNamespace(
            id=701,
            dataset_id=7,
            version_number=5,
            is_current_published=True,
            is_current_draft=False,
            grain_key='per_scope_per_year',
            output_schema_json=[
                {'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'},
                {'key': 'tanggal', 'label': 'Tanggal', 'type': 'date'},
            ],
            dimension_definitions_json=[],
            metric_definitions_json=[
                {'key': 'capaian_total', 'label': 'Capaian Total', 'type': 'number'},
                {'key': 'achievement_pct', 'label': 'Persentase Capaian', 'type': 'number'},
            ],
        )
        report_definition_repository = StubReportDefinitionRepository()
        report_version_repository = StubReportVersionRepository()
        dataset_repository = StubDatasetRepository([dataset])
        dataset_version_repository = StubDatasetVersionRepository([dataset_version])
        service = AnalyticsReportService(
            report_definition_repository=report_definition_repository,
            report_version_repository=report_version_repository,
            dataset_repository=dataset_repository,
            dataset_version_repository=dataset_version_repository,
        )

        bundle = service.create_report_bundle(
            {
                'report': {
                    'report_key': 'pk-kanwil',
                    'dataset_id': 7,
                    'name': 'PK Kanwil',
                    'report_type': 'performance_report',
                    'report_family': 'pk',
                    'category_key': 'pk',
                },
                'draft_version': {
                    'dataset_version_id': 701,
                    'title': 'PK Kanwil 2026',
                },
            }
        )

        assert bundle['report'].report_type == AnalyticsReportDefinition.TYPE_SCORECARD
        assert bundle['report'].settings_json['report_family'] == 'pk'
        assert bundle['draft_version'].structure_json['layout']['report_family'] == 'pk'
        assert bundle['draft_version'].structure_json['layout']['block_order_strategy'] == 'explicit_order'
        assert bundle['draft_version'].structure_json['period_preset_config']['supported_period_modes'] == ['quarterly', 'semester', 'yearly']
        assert [block['type'] for block in bundle['draft_version'].structure_json['blocks']] == [
            'metric_cards',
            'detail_table',
            'plotly_timeseries',
            'narrative',
        ]


def test_report_service_preserves_item_based_report_structure():
    from app.modules.analytics.services import AnalyticsReportService

    dataset = SimpleNamespace(id=7, dataset_key='dataset-pk', name='Dataset PK', settings_json={})
    dataset_version = SimpleNamespace(
        id=701,
        dataset_id=7,
        dataset=dataset,
        version_number=2,
        grain_key='per_scope_per_year',
        output_schema_json=[{'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'}],
        dimension_definitions_json=[{'key': 'nama_indikator', 'label': 'Nama Indikator', 'type': 'string'}],
        metric_definitions_json=[
            {'key': 'nilai_realisasi', 'label': 'Nilai Realisasi', 'type': 'number'},
            {'key': 'target_kinerja', 'label': 'Target Kinerja', 'type': 'number'},
        ],
    )
    service = AnalyticsReportService(
        report_definition_repository=StubReportDefinitionRepository(),
        report_version_repository=StubReportVersionRepository(),
        dataset_repository=StubDatasetRepository([dataset]),
        dataset_version_repository=StubDatasetVersionRepository([dataset_version]),
    )

    bundle = service.create_report_bundle({
        'report': {
            'report_key': 'perjanjian-kinerja',
            'name': 'Perjanjian Kinerja',
            'report_type': 'pk',
            'report_family': 'pk',
            'category_key': 'pk',
        },
        'draft_version': {
            'title': 'Perjanjian Kinerja 2026',
            'report_items': [
                {
                    'item_key': 'indikator-1',
                    'name': 'indikator 1',
                    'datasets': [
                        {
                            'dataset_id': 7,
                            'dataset_version_id': 701,
                            'actual_metric_key': 'nilai_realisasi',
                            'target_metric_key': 'target_kinerja',
                            'chart_type': 'bar',
                            'table_column_keys': ['nama_indikator', 'nilai_realisasi', 'target_kinerja'],
                        }
                    ],
                }
            ],
            'data_sources': [
                {'alias': 'indikator_1_dataset_pk', 'dataset_id': 7, 'dataset_version_id': 701}
            ],
            'blocks': [
                {
                    'type': 'metric_cards',
                    'title': 'indikator 1 — Aktual vs Target',
                    'data_source_alias': 'indikator_1_dataset_pk',
                    'config': {
                        'metric_keys': ['nilai_realisasi', 'target_kinerja'],
                        'actual_metric_key': 'nilai_realisasi',
                        'target_metric_key': 'target_kinerja',
                    },
                }
            ],
        },
    })

    structure = bundle['draft_version'].structure_json
    assert structure['report_items'][0]['name'] == 'indikator 1'
    assert structure['report_items'][0]['datasets'][0]['actual_metric_key'] == 'nilai_realisasi'
    assert structure['report_items'][0]['datasets'][0]['target_metric_key'] == 'target_kinerja'
    assert structure['data_sources'][0]['alias'] == 'indikator_1_dataset_pk'
    assert structure['blocks'][0]['config']['actual_metric_key'] == 'nilai_realisasi'
    assert structure['blocks'][0]['config']['target_metric_key'] == 'target_kinerja'
