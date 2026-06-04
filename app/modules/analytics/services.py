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


class AnalyticsIndicatorResultService(BaseService):
    def __init__(
        self,
        result_repository=None,
        progress_entry_repository=None,
        indicator_version_repository=None,
    ):
        super().__init__(repository=result_repository or AnalyticsIndicatorResultRepository())
        self.progress_entry_repository = (
            progress_entry_repository or AnalyticsIndicatorProgressEntryRepository()
        )
        self.indicator_version_repository = (
            indicator_version_repository or AnalyticsIndicatorVersionRepository()
        )

    def record_result(self, data, actor=None):
        source_snapshot_json = data.get('source_snapshot_json') or {}
        indicator_version_id = data.get('indicator_version_id')
        indicator_version = None
        if indicator_version_id is not None:
            indicator_version = self.indicator_version_repository.get_by_id(indicator_version_id)

        if not source_snapshot_json and indicator_version:
            definition = getattr(indicator_version, 'definition', None)
            source_mode = (
                getattr(definition, 'source_mode', None)
                or AnalyticsIndicatorDefinition.SOURCE_MODE_DATASET_DRIVEN
            )
            source_snapshot_json = {
                'source_mode': source_mode,
                'dataset_id': indicator_version.dataset_id,
                'dataset_version_id': indicator_version.dataset_version_id,
                'dataset_run_id': data.get('dataset_run_id'),
                'indicator_version_id': indicator_version.id,
            }

        result = AnalyticsIndicatorResult(
            uuid=str(uuid.uuid4()),
            indicator_version_id=indicator_version_id,
            dataset_run_id=data.get('dataset_run_id'),
            reporting_year=data.get('reporting_year'),
            reporting_period_id=data.get('reporting_period_id'),
            status=data.get('status', AnalyticsIndicatorResult.STATUS_DRAFT),
            completion_status=data.get('completion_status', AnalyticsIndicatorResult.COMPLETION_NOT_STARTED),
            measured_value=data.get('measured_value'),
            target_value=data.get('target_value'),
            achievement_percentage=data.get('achievement_percentage'),
            qualitative_summary=data.get('qualitative_summary'),
            constraint_notes=data.get('constraint_notes'),
            narrative_context_json=data.get('narrative_context_json') or {},
            source_snapshot_json=source_snapshot_json,
            calculated_at=data.get('calculated_at'),
        )
        self._apply_actor_audit(result, actor, action='create')
        return self.repository.save(result)

    def record_progress_entry(self, data, actor=None):
        entry = AnalyticsIndicatorProgressEntry(
            uuid=str(uuid.uuid4()),
            indicator_version_id=data.get('indicator_version_id'),
            reporting_year=data.get('reporting_year'),
            reporting_period_id=data.get('reporting_period_id'),
            status=data.get('status', AnalyticsIndicatorProgressEntry.STATUS_DRAFT),
            progress_percent=data.get('progress_percent'),
            qualitative_summary=data.get('qualitative_summary'),
            constraint_notes=data.get('constraint_notes'),
            narrative_context_json=data.get('narrative_context_json') or {},
            summary_json=data.get('summary_json') or {},
        )
        for item_data in data.get('items') or []:
            item = AnalyticsIndicatorProgressItem(
                uuid=str(uuid.uuid4()),
                item_order=item_data.get('item_order', 1),
                status=item_data.get('status', AnalyticsIndicatorProgressItem.STATUS_PENDING),
                title=item_data.get('title') or 'Untitled progress item',
                description=item_data.get('description'),
                narrative_context_json=item_data.get('narrative_context_json') or {},
            )
            self._apply_actor_audit(item, actor, action='create')
            entry.items.append(item)
        self._apply_actor_audit(entry, actor, action='create')
        return self.progress_entry_repository.save(entry)

    def sync_result_from_progress(self, progress_entry_id, actor=None):
        progress_entry = self.progress_entry_repository.get_by_id(progress_entry_id)
        if not progress_entry:
            raise ValueError('Analytics indicator progress entry tidak ditemukan.')

        existing_result = self.repository.get_latest_for_period(
            indicator_version_id=progress_entry.indicator_version_id,
            reporting_year=progress_entry.reporting_year,
            reporting_period_id=progress_entry.reporting_period_id,
        )

        result = existing_result or AnalyticsIndicatorResult(
            uuid=str(uuid.uuid4()),
            indicator_version_id=progress_entry.indicator_version_id,
            reporting_year=progress_entry.reporting_year,
            reporting_period_id=progress_entry.reporting_period_id,
        )
        result.qualitative_summary = progress_entry.qualitative_summary
        result.constraint_notes = progress_entry.constraint_notes
        result.narrative_context_json = progress_entry.narrative_context_json or {}
        result.completion_status = (
            AnalyticsIndicatorResult.COMPLETION_COMPLETED
            if progress_entry.status == AnalyticsIndicatorProgressEntry.STATUS_COMPLETED
            else AnalyticsIndicatorResult.COMPLETION_IN_PROGRESS
        )
        result.status = AnalyticsIndicatorResult.STATUS_DRAFT
        result.calculated_at = now_utc()
        self._apply_actor_audit(result, actor, action='update' if existing_result else 'create')
        return self.repository.save(result)

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


class AnalyticsQueryService(BaseService):
    def __init__(
        self,
        report_definition_repository=None,
        report_version_repository=None,
        indicator_definition_repository=None,
        indicator_version_repository=None,
        report_version_indicator_repository=None,
        result_repository=None,
        progress_entry_repository=None,
    ):
        super().__init__(repository=report_definition_repository or AnalyticsReportDefinitionRepository())
        self.report_version_repository = report_version_repository or AnalyticsReportVersionRepository()
        self.indicator_definition_repository = (
            indicator_definition_repository or AnalyticsIndicatorDefinitionRepository()
        )
        self.indicator_version_repository = (
            indicator_version_repository or AnalyticsIndicatorVersionRepository()
        )
        self.report_version_indicator_repository = (
            report_version_indicator_repository or AnalyticsReportVersionIndicatorRepository()
        )
        self.result_repository = result_repository or AnalyticsIndicatorResultRepository()
        self.progress_entry_repository = (
            progress_entry_repository or AnalyticsIndicatorProgressEntryRepository()
        )

    def list_reports(self):
        items = []
        for report in self.repository.get_all():
            draft_version = self.report_version_repository.get_draft_version(report.id)
            published_version = self.report_version_repository.get_published_version(report.id)
            active_version = draft_version or published_version
            mappings = []
            if active_version:
                mappings = self.report_version_indicator_repository.list_by_report_version(active_version.id)
            items.append({
                'report': report,
                'draft_version': draft_version,
                'published_version': published_version,
                'indicator_mapping_count': len(mappings),
            })
        return items

    def get_report_workspace(self, report_definition_id):
        report = self.repository.get_by_id(report_definition_id)
        if not report:
            raise ValueError('Analytics report definition tidak ditemukan.')

        draft_version = self.report_version_repository.get_draft_version(report_definition_id)
        published_version = self.report_version_repository.get_published_version(report_definition_id)
        versions = self.report_version_repository.list_versions(report_definition_id)
        active_version = draft_version or published_version
        indicator_mappings = []

        if active_version:
            for mapping in self.report_version_indicator_repository.list_by_report_version(active_version.id):
                indicator_version = getattr(mapping, 'indicator_version', None)
                indicator_definition = getattr(indicator_version, 'definition', None) if indicator_version else None
                indicator_mappings.append({
                    'mapping': mapping,
                    'indicator_version': indicator_version,
                    'indicator_definition': indicator_definition,
                })

        return {
            'report': report,
            'draft_version': draft_version,
            'published_version': published_version,
            'versions': versions,
            'indicator_mappings': indicator_mappings,
        }

    def list_indicators(self):
        items = []
        for indicator in self.indicator_definition_repository.get_all():
            draft_version = self.indicator_version_repository.get_draft_version(indicator.id)
            published_version = self.indicator_version_repository.get_published_version(indicator.id)
            active_version = draft_version or published_version
            latest_result = None
            latest_progress_entry = None
            if active_version:
                latest_result = self.result_repository.get_latest_for_period(active_version.id)
                latest_progress_entry = self.progress_entry_repository.get_latest_for_period(active_version.id)
            items.append({
                'indicator': indicator,
                'draft_version': draft_version,
                'published_version': published_version,
                'latest_result': latest_result,
                'latest_progress_entry': latest_progress_entry,
            })
        return items

    def get_indicator_workspace(self, indicator_definition_id):
        indicator = self.indicator_definition_repository.get_by_id(indicator_definition_id)
        if not indicator:
            raise ValueError('Analytics indicator definition tidak ditemukan.')

        draft_version = self.indicator_version_repository.get_draft_version(indicator_definition_id)
        published_version = self.indicator_version_repository.get_published_version(indicator_definition_id)
        versions = self.indicator_version_repository.list_versions(indicator_definition_id)
        active_version = draft_version or published_version
        results = []
        progress_entries = []

        if active_version:
            results = self.result_repository.list_by_indicator_version(active_version.id)
            progress_entries = self.progress_entry_repository.list_by_indicator_version(active_version.id)

        return {
            'indicator': indicator,
            'draft_version': draft_version,
            'published_version': published_version,
            'versions': versions,
            'results': results,
            'progress_entries': progress_entries,
        }

    def list_indicator_results(self, indicator_version_id=None, reporting_year=None, reporting_period_id=None, limit=50):
        return self.result_repository.list_filtered(
            indicator_version_id=indicator_version_id,
            reporting_year=reporting_year,
            reporting_period_id=reporting_period_id,
            limit=limit,
        )
