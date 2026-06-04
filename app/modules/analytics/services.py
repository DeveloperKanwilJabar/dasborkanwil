import uuid

from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc

from .models import (
    AnalyticsIndicatorDefinition,
    AnalyticsIndicatorProgressEntry,
    AnalyticsIndicatorProgressItem,
    AnalyticsIndicatorResult,
    AnalyticsIndicatorVersion,
    AnalyticsReportDefinition,
    AnalyticsReportVersion,
    AnalyticsReportVersionIndicator,
)
from .repositories import (
    AnalyticsIndicatorDefinitionRepository,
    AnalyticsIndicatorProgressEntryRepository,
    AnalyticsIndicatorResultRepository,
    AnalyticsIndicatorVersionRepository,
    AnalyticsReportDefinitionRepository,
    AnalyticsReportVersionIndicatorRepository,
    AnalyticsReportVersionRepository,
)


class AnalyticsReportService(BaseService):
    def __init__(self, report_definition_repository=None, report_version_repository=None):
        super().__init__(repository=report_definition_repository or AnalyticsReportDefinitionRepository())
        self.version_repository = report_version_repository or AnalyticsReportVersionRepository()

    def create_report_definition(self, data, actor=None):
        report = AnalyticsReportDefinition(
            uuid=str(uuid.uuid4()),
            report_key=data.get('report_key'),
            name=data.get('name') or data.get('report_key') or 'Untitled report',
            description=data.get('description'),
            report_type=data.get('report_type', AnalyticsReportDefinition.TYPE_CUSTOM),
            category_key=data.get('category_key'),
            status=data.get('status', AnalyticsReportDefinition.STATUS_DRAFT),
            is_active=data.get('is_active', True),
            settings_json=data.get('settings_json') or {},
            tags_json=data.get('tags_json') or [],
        )
        self._apply_actor_audit(report, actor, action='create')
        return self.repository.save(report)

    def create_report_version(self, report_definition_id, data, actor=None):
        version = AnalyticsReportVersion(
            uuid=str(uuid.uuid4()),
            report_definition_id=report_definition_id,
            version_number=self.version_repository.get_next_version_number(report_definition_id),
            status=data.get('status', AnalyticsReportVersion.STATUS_DRAFT),
            is_current_draft=data.get('is_current_draft', True),
            is_current_published=data.get('is_current_published', False),
            title=data.get('title') or f'Report version {report_definition_id}',
            meta_description=data.get('meta_description'),
            structure_json=data.get('structure_json') or {},
            narrative_guidance_json=data.get('narrative_guidance_json') or {},
            published_at=data.get('published_at'),
        )
        self._apply_actor_audit(version, actor, action='create')
        return self.version_repository.save(version)

    def publish_report_version(self, version_id, actor=None):
        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ValueError('Analytics report version tidak ditemukan.')

        try:
            self.version_repository.archive_published_others(
                version.report_definition_id,
                except_version_id=version.id,
            )
            version.status = AnalyticsReportVersion.STATUS_PUBLISHED
            version.is_current_draft = False
            version.is_current_published = True
            version.published_at = now_utc()
            self._apply_actor_audit(version, actor, action='update')
            saved_version = self.version_repository.save(version)

            report_definition = self.repository.get_by_id(version.report_definition_id)
            if report_definition:
                report_definition.status = AnalyticsReportDefinition.STATUS_ACTIVE
                report_definition.is_active = True
                self._apply_actor_audit(report_definition, actor, action='update')
                self.repository.save(report_definition)

            return saved_version
        except Exception:
            db.session.rollback()
            raise

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        if not actor:
            return obj
        actor_id = getattr(actor, 'id', None)
        actor_uuid = getattr(actor, 'uuid', None)
        if action == 'create':
            obj.created_by = actor_id
            obj.created_by_uuid = actor_uuid
        obj.updated_by = actor_id
        obj.updated_by_uuid = actor_uuid
        return obj


class AnalyticsIndicatorService(BaseService):
    def __init__(
        self,
        indicator_definition_repository=None,
        indicator_version_repository=None,
        report_version_indicator_repository=None,
    ):
        super().__init__(repository=indicator_definition_repository or AnalyticsIndicatorDefinitionRepository())
        self.version_repository = indicator_version_repository or AnalyticsIndicatorVersionRepository()
        self.report_version_indicator_repository = (
            report_version_indicator_repository or AnalyticsReportVersionIndicatorRepository()
        )

    def create_indicator_definition(self, data, actor=None):
        indicator = AnalyticsIndicatorDefinition(
            uuid=str(uuid.uuid4()),
            indicator_key=data.get('indicator_key'),
            indicator_code=data.get('indicator_code'),
            name=data.get('name') or data.get('indicator_key') or 'Untitled indicator',
            description=data.get('description'),
            source_mode=data.get('source_mode', AnalyticsIndicatorDefinition.SOURCE_MODE_DATASET_DRIVEN),
            calculation_type=data.get('calculation_type', AnalyticsIndicatorDefinition.CALCULATION_ABSOLUTE_COUNT),
            target_source_type=data.get('target_source_type', AnalyticsIndicatorDefinition.TARGET_SOURCE_MANUAL_CENTRAL),
            status=data.get('status', AnalyticsIndicatorDefinition.STATUS_DRAFT),
            is_active=data.get('is_active', True),
            settings_json=data.get('settings_json') or {},
            tags_json=data.get('tags_json') or [],
        )
        self._apply_actor_audit(indicator, actor, action='create')
        return self.repository.save(indicator)

    def create_indicator_version(self, indicator_definition_id, data, actor=None):
        indicator_definition = self.repository.get_by_id(indicator_definition_id)
        if not indicator_definition:
            raise ValueError('Analytics indicator definition tidak ditemukan.')

        dataset_id = data.get('dataset_id')
        dataset_version_id = data.get('dataset_version_id')
        source_mode = getattr(
            indicator_definition,
            'source_mode',
            AnalyticsIndicatorDefinition.SOURCE_MODE_DATASET_DRIVEN,
        )

        if source_mode == AnalyticsIndicatorDefinition.SOURCE_MODE_DATASET_DRIVEN:
            if not dataset_id or not dataset_version_id:
                raise ValueError('Indicator dataset_driven wajib memiliki dataset_id dan dataset_version_id.')
        elif source_mode == AnalyticsIndicatorDefinition.SOURCE_MODE_MANUAL_INPUT:
            if dataset_id or dataset_version_id:
                raise ValueError('Indicator manual_input tidak boleh membawa dataset_id atau dataset_version_id.')

        version = AnalyticsIndicatorVersion(
            uuid=str(uuid.uuid4()),
            indicator_definition_id=indicator_definition_id,
            version_number=self.version_repository.get_next_version_number(indicator_definition_id),
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            status=data.get('status', AnalyticsIndicatorVersion.STATUS_DRAFT),
            is_current_draft=data.get('is_current_draft', True),
            is_current_published=data.get('is_current_published', False),
            period_mode=data.get('period_mode', AnalyticsIndicatorVersion.PERIOD_MODE_YEARLY),
            aggregation_strategy=data.get('aggregation_strategy', AnalyticsIndicatorVersion.AGGREGATION_SUM),
            unit_label=data.get('unit_label'),
            meta_description=data.get('meta_description'),
            formula_json=data.get('formula_json') or {},
            target_config_json=data.get('target_config_json') or {},
            narrative_guidance_json=data.get('narrative_guidance_json') or {},
            threshold_rules_json=data.get('threshold_rules_json') or [],
            published_at=data.get('published_at'),
        )
        self._apply_actor_audit(version, actor, action='create')
        return self.version_repository.save(version)

    def publish_indicator_version(self, version_id, actor=None):
        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ValueError('Analytics indicator version tidak ditemukan.')

        try:
            self.version_repository.archive_published_others(
                version.indicator_definition_id,
                except_version_id=version.id,
            )
            version.status = AnalyticsIndicatorVersion.STATUS_PUBLISHED
            version.is_current_draft = False
            version.is_current_published = True
            version.published_at = now_utc()
            self._apply_actor_audit(version, actor, action='update')
            saved_version = self.version_repository.save(version)

            indicator_definition = self.repository.get_by_id(version.indicator_definition_id)
            if indicator_definition:
                indicator_definition.status = AnalyticsIndicatorDefinition.STATUS_ACTIVE
                indicator_definition.is_active = True
                self._apply_actor_audit(indicator_definition, actor, action='update')
                self.repository.save(indicator_definition)

            return saved_version
        except Exception:
            db.session.rollback()
            raise

    def attach_indicator_to_report_version(
        self,
        report_version_id,
        indicator_version_id,
        data=None,
        actor=None,
    ):
        data = data or {}
        indicator_version = self.version_repository.get_by_id(indicator_version_id)
        if not indicator_version:
            raise ValueError('Analytics indicator version tidak ditemukan.')
        if getattr(indicator_version, 'status', None) != AnalyticsIndicatorVersion.STATUS_PUBLISHED:
            raise ValueError('Hanya indicator version published yang boleh di-attach ke report version.')

        mapping = AnalyticsReportVersionIndicator(
            uuid=str(uuid.uuid4()),
            report_version_id=report_version_id,
            indicator_version_id=indicator_version_id,
            item_order=data.get('item_order', 1),
            display_label=data.get('display_label'),
            section_key=data.get('section_key'),
            config_json=data.get('config_json') or {},
        )
        self._apply_actor_audit(mapping, actor, action='create')
        return self.report_version_indicator_repository.save(mapping)

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        if not actor:
            return obj
        actor_id = getattr(actor, 'id', None)
        actor_uuid = getattr(actor, 'uuid', None)
        if action == 'create':
            obj.created_by = actor_id
            obj.created_by_uuid = actor_uuid
        obj.updated_by = actor_id
        obj.updated_by_uuid = actor_uuid
        return obj
