from decimal import Decimal
from types import SimpleNamespace

from app import create_app
from app.modules.analytics.models import (
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


def test_create_publish_indicator_and_report_flow_archives_previous_versions():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import AnalyticsIndicatorService, AnalyticsReportService

        actor = SimpleNamespace(id=7, uuid='actor-uuid')

        report_definition = AnalyticsReportDefinition(
            id=21,
            uuid='report-def-uuid',
            report_key='pk-kanwil',
            name='PK Kanwil',
            status=AnalyticsReportDefinition.STATUS_DRAFT,
        )
        old_report_version = AnalyticsReportVersion(
            id=31,
            uuid='report-version-uuid-1',
            report_definition_id=21,
            version_number=1,
            status=AnalyticsReportVersion.STATUS_PUBLISHED,
            is_current_draft=False,
            is_current_published=True,
            title='PK 2025',
        )
        report_definition_repository = StubReportDefinitionRepository([report_definition])
        report_version_repository = StubReportVersionRepository([old_report_version])
        report_service = AnalyticsReportService(
            report_definition_repository=report_definition_repository,
            report_version_repository=report_version_repository,
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
