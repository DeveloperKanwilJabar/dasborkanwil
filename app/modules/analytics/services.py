"""Service layer domain analytics.

Modul ini mengelola dataset analytics, run dataset, definisi report, indikator, hasil indikator, progress entry, dan query workspace yang dipakai UI maupun API analytics."""

import uuid

from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc

from .models import (
    AnalyticsDataset,
    AnalyticsDatasetRun,
    AnalyticsDatasetVersion,
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
    AnalyticsDatasetRepository,
    AnalyticsDatasetRunRepository,
    AnalyticsDatasetVersionRepository,
    AnalyticsIndicatorDefinitionRepository,
    AnalyticsIndicatorProgressEntryRepository,
    AnalyticsIndicatorResultRepository,
    AnalyticsIndicatorVersionRepository,
    AnalyticsReportDefinitionRepository,
    AnalyticsReportVersionIndicatorRepository,
    AnalyticsReportVersionRepository,
)


class AnalyticsDatasetService(BaseService):
    """Service CRUD bisnis untuk dataset analytics dan versi datasetnya.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = AnalyticsDatasetService()
    """

    def __init__(self, dataset_repository=None, dataset_version_repository=None):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            dataset_repository (Any): Parameter `dataset_repository` untuk operasi init.
            dataset_version_repository (Any): Parameter `dataset_version_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = AnalyticsDatasetService()
        """

        super().__init__(repository=dataset_repository or AnalyticsDatasetRepository())
        self.version_repository = dataset_version_repository or AnalyticsDatasetVersionRepository()

    def create_dataset(self, data, actor=None):
        """Membuat definisi dataset analytics baru.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_dataset(data=..., actor=...)
        """

        dataset = AnalyticsDataset(
            uuid=str(uuid.uuid4()),
            dataset_key=data.get('dataset_key'),
            name=data.get('name') or data.get('dataset_key') or 'Untitled dataset',
            description=data.get('description'),
            source_domain=data.get('source_domain', AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION),
            source_type=data.get('source_type', AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT),
            primary_source_ref=data.get('primary_source_ref'),
            status=data.get('status', AnalyticsDataset.STATUS_DRAFT),
            is_active=data.get('is_active', True),
            is_year_scoped=data.get('is_year_scoped', True),
            default_reporting_year_mode=data.get(
                'default_reporting_year_mode',
                AnalyticsDataset.REPORTING_YEAR_MODE_ACTIVE,
            ),
            owner_scope_type=data.get('owner_scope_type'),
            owner_scope_code=data.get('owner_scope_code'),
            owner_scope_name=data.get('owner_scope_name'),
            owner_scope_path=data.get('owner_scope_path') or [],
            settings_json=data.get('settings_json') or {},
            tags_json=data.get('tags_json') or [],
        )
        self._apply_actor_audit(dataset, actor, action='create')
        return self.repository.save(dataset)

    def create_dataset_version(self, dataset_id, data, actor=None):
        """Membuat version dataset analytics baru.

        Args:
            dataset_id (Any): Primary key internal dataset analytics target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_dataset_version(dataset_id=..., data=..., actor=...)
        """

        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')

        version = AnalyticsDatasetVersion(
            uuid=str(uuid.uuid4()),
            dataset_id=dataset_id,
            version_number=self.version_repository.get_next_version_number(dataset_id),
            status=data.get('status', AnalyticsDatasetVersion.STATUS_DRAFT),
            is_current_draft=data.get('is_current_draft', True),
            is_current_published=data.get('is_current_published', False),
            source_contract_json=data.get('source_contract_json') or {},
            query_spec_json=data.get('query_spec_json') or {},
            transform_spec_json=data.get('transform_spec_json') or {},
            join_registry_spec_json=data.get('join_registry_spec_json') or [],
            grain_key=data.get('grain_key', AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR),
            output_schema_json=data.get('output_schema_json') or [],
            dimension_definitions_json=data.get('dimension_definitions_json') or [],
            metric_definitions_json=data.get('metric_definitions_json') or [],
            default_filters_json=data.get('default_filters_json') or {},
            sort_spec_json=data.get('sort_spec_json') or [],
            freshness_source_type=data.get(
                'freshness_source_type',
                AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
            ),
            freshness_source_ref=data.get('freshness_source_ref'),
            freshness_strategy=data.get(
                'freshness_strategy',
                AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
            ),
            freshness_policy_json=data.get('freshness_policy_json') or {},
            publish_notes=data.get('publish_notes'),
            published_at=data.get('published_at'),
        )
        self._apply_actor_audit(version, actor, action='create')
        return self.version_repository.save(version)

    def publish_dataset_version(self, version_id, actor=None):
        """Mempublish dataset version dan mengarsipkan version published lain.

        Args:
            version_id (Any): Primary key internal version target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.publish_dataset_version(version_id=..., actor=...)
        """

        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ValueError('Analytics dataset version tidak ditemukan.')

        try:
            self.version_repository.archive_published_others(
                version.dataset_id,
                except_version_id=version.id,
            )
            version.status = AnalyticsDatasetVersion.STATUS_PUBLISHED
            version.is_current_draft = False
            version.is_current_published = True
            version.published_at = now_utc()
            self._apply_actor_audit(version, actor, action='update')
            saved_version = self.version_repository.save(version)

            dataset = self.repository.get_by_id(version.dataset_id)
            if dataset:
                dataset.status = AnalyticsDataset.STATUS_ACTIVE
                dataset.is_active = True
                self._apply_actor_audit(dataset, actor, action='update')
                self.repository.save(dataset)

            return saved_version
        except Exception:
            db.session.rollback()
            raise

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        """Helper internal untuk apply actor audit.

        Args:
            obj (Any): Parameter `obj` untuk operasi apply actor audit.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            action (Any): Parameter `action` untuk operasi apply actor audit.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._apply_actor_audit(obj=..., actor=..., action=...)
        """

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


class AnalyticsDatasetRunService(BaseService):
    """Service untuk menandai lifecycle eksekusi dataset run.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = AnalyticsDatasetRunService()
    """

    def __init__(
        self,
        dataset_repository=None,
        dataset_version_repository=None,
        dataset_run_repository=None,
    ):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            dataset_repository (Any): Parameter `dataset_repository` untuk operasi init.
            dataset_version_repository (Any): Parameter `dataset_version_repository` untuk operasi init.
            dataset_run_repository (Any): Parameter `dataset_run_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = AnalyticsDatasetRunService()
        """

        super().__init__(repository=dataset_run_repository or AnalyticsDatasetRunRepository())
        self.dataset_repository = dataset_repository or AnalyticsDatasetRepository()
        self.dataset_version_repository = dataset_version_repository or AnalyticsDatasetVersionRepository()

    def start_run(self, dataset_id, dataset_version_id, data=None, actor=None):
        """Membuka run dataset analytics baru dengan status running.

        Args:
            dataset_id (Any): Primary key internal dataset analytics target.
            dataset_version_id (Any): Primary key internal dataset version target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.start_run(dataset_id=..., dataset_version_id=..., data=...)
        """

        data = data or {}
        dataset = self.dataset_repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')

        dataset_version = self.dataset_version_repository.get_by_id(dataset_version_id)
        if not dataset_version or dataset_version.dataset_id != dataset_id:
            raise ValueError('Analytics dataset version tidak ditemukan.')
        if getattr(dataset_version, 'status', None) != AnalyticsDatasetVersion.STATUS_PUBLISHED:
            raise ValueError('Hanya dataset version published yang boleh menjalankan run.')

        run = AnalyticsDatasetRun(
            uuid=str(uuid.uuid4()),
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            run_key=data.get('run_key') or f'dataset-run-{uuid.uuid4()}',
            trigger_type=data.get('trigger_type', AnalyticsDatasetRun.TRIGGER_MANUAL),
            trigger_ref=data.get('trigger_ref'),
            requested_reporting_year=data.get('requested_reporting_year'),
            requested_reporting_period_id=data.get('requested_reporting_period_id'),
            requested_filters_json=data.get('requested_filters_json') or {},
            status=AnalyticsDatasetRun.STATUS_RUNNING,
            started_at=data.get('started_at') or now_utc(),
            freshness_status=data.get('freshness_status', AnalyticsDatasetRun.FRESHNESS_UNKNOWN),
            source_snapshot_json=data.get('source_snapshot_json') or {},
        )
        self._apply_actor_audit(run, actor, action='create')
        return self.repository.save(run)

    def complete_run(self, run_id, data=None, actor=None):
        """Menutup dataset run sebagai sukses dan menyimpan preview hasilnya.

        Args:
            run_id (Any): Primary key internal dataset run target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.complete_run(run_id=..., data=..., actor=...)
        """

        data = data or {}
        run = self.repository.get_by_id(run_id)
        if not run:
            raise ValueError('Analytics dataset run tidak ditemukan.')

        run.status = AnalyticsDatasetRun.STATUS_SUCCEEDED
        run.finished_at = data.get('finished_at') or now_utc()
        run.result_row_count = data.get('result_row_count')
        run.result_schema_json = data.get('result_schema_json') or []
        run.result_preview_json = data.get('result_preview_json') or []
        run.materialization_ref = data.get('materialization_ref')
        run.summary_json = data.get('summary_json') or {}
        run.error_code = None
        run.error_message = None
        run.error_detail_json = {}
        self._apply_actor_audit(run, actor, action='update')
        return self.repository.save(run)

    def fail_run(self, run_id, data=None, actor=None):
        """Menutup dataset run sebagai gagal beserta error detailnya.

        Args:
            run_id (Any): Primary key internal dataset run target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.fail_run(run_id=..., data=..., actor=...)
        """

        data = data or {}
        run = self.repository.get_by_id(run_id)
        if not run:
            raise ValueError('Analytics dataset run tidak ditemukan.')

        run.status = AnalyticsDatasetRun.STATUS_FAILED
        run.finished_at = data.get('finished_at') or now_utc()
        run.error_code = data.get('error_code')
        run.error_message = data.get('error_message')
        run.error_detail_json = data.get('error_detail_json') or {}
        self._apply_actor_audit(run, actor, action='update')
        return self.repository.save(run)

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        """Helper internal untuk apply actor audit.

        Args:
            obj (Any): Parameter `obj` untuk operasi apply actor audit.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            action (Any): Parameter `action` untuk operasi apply actor audit.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._apply_actor_audit(obj=..., actor=..., action=...)
        """

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


class AnalyticsReportService(BaseService):
    """Service pengelolaan definisi report analytics dan versinya.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = AnalyticsReportService()
    """

    def __init__(self, report_definition_repository=None, report_version_repository=None):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            report_definition_repository (Any): Parameter `report_definition_repository` untuk operasi init.
            report_version_repository (Any): Parameter `report_version_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = AnalyticsReportService()
        """

        super().__init__(repository=report_definition_repository or AnalyticsReportDefinitionRepository())
        self.version_repository = report_version_repository or AnalyticsReportVersionRepository()

    def create_report_definition(self, data, actor=None):
        """Membuat definisi report analytics baru.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_report_definition(data=..., actor=...)
        """

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
        """Membuat version report analytics baru.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_report_version(report_definition_id=..., data=..., actor=...)
        """

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
        """Mempublish report version dan menandai definisi report sebagai active.

        Args:
            version_id (Any): Primary key internal version target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.publish_report_version(version_id=..., actor=...)
        """

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
        """Helper internal untuk apply actor audit.

        Args:
            obj (Any): Parameter `obj` untuk operasi apply actor audit.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            action (Any): Parameter `action` untuk operasi apply actor audit.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._apply_actor_audit(obj=..., actor=..., action=...)
        """

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
    """Service pengelolaan definisi indikator, versi indikator, dan attachment ke report.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = AnalyticsIndicatorService()
    """

    def __init__(
        self,
        indicator_definition_repository=None,
        indicator_version_repository=None,
        report_version_indicator_repository=None,
    ):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            indicator_definition_repository (Any): Parameter `indicator_definition_repository` untuk operasi init.
            indicator_version_repository (Any): Parameter `indicator_version_repository` untuk operasi init.
            report_version_indicator_repository (Any): Parameter `report_version_indicator_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = AnalyticsIndicatorService()
        """

        super().__init__(repository=indicator_definition_repository or AnalyticsIndicatorDefinitionRepository())
        self.version_repository = indicator_version_repository or AnalyticsIndicatorVersionRepository()
        self.report_version_indicator_repository = (
            report_version_indicator_repository or AnalyticsReportVersionIndicatorRepository()
        )

    def create_indicator_definition(self, data, actor=None):
        """Membuat definisi indikator analytics baru.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_indicator_definition(data=..., actor=...)
        """

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
        """Membuat version indikator dengan validasi source mode dataset/manual.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_indicator_version(indicator_definition_id=..., data=..., actor=...)
        """

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
        """Mempublish indicator version dan mengaktifkan definition induknya.

        Args:
            version_id (Any): Primary key internal version target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.publish_indicator_version(version_id=..., actor=...)
        """

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
        """Menghubungkan indicator version published ke report version tertentu.

        Args:
            report_version_id (Any): Primary key internal version report target.
            indicator_version_id (Any): Primary key internal version indikator target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service.attach_indicator_to_report_version(report_version_id=..., indicator_version_id=..., data=...)
        """

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
        """Helper internal untuk apply actor audit.

        Args:
            obj (Any): Parameter `obj` untuk operasi apply actor audit.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            action (Any): Parameter `action` untuk operasi apply actor audit.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._apply_actor_audit(obj=..., actor=..., action=...)
        """

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
    """Service pencatatan hasil indikator dan progress entry periodik.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = AnalyticsIndicatorResultService()
    """

    def __init__(
        self,
        result_repository=None,
        progress_entry_repository=None,
        indicator_version_repository=None,
    ):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            result_repository (Any): Parameter `result_repository` untuk operasi init.
            progress_entry_repository (Any): Parameter `progress_entry_repository` untuk operasi init.
            indicator_version_repository (Any): Parameter `indicator_version_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = AnalyticsIndicatorResultService()
        """

        super().__init__(repository=result_repository or AnalyticsIndicatorResultRepository())
        self.progress_entry_repository = (
            progress_entry_repository or AnalyticsIndicatorProgressEntryRepository()
        )
        self.indicator_version_repository = (
            indicator_version_repository or AnalyticsIndicatorVersionRepository()
        )

    def record_result(self, data, actor=None):
        """Mencatat hasil indikator terhitung atau hasil input manual untuk suatu periode.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.record_result(data=..., actor=...)
        """

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
        """Mencatat progress entry periodik untuk indikator.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.record_progress_entry(data=..., actor=...)
        """

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
        """Menyinkronkan progress entry menjadi result indikator ringkasan.

        Args:
            progress_entry_id (Any): Primary key internal progress entry target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service.sync_result_from_progress(progress_entry_id=..., actor=...)
        """

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
        """Helper internal untuk apply actor audit.

        Args:
            obj (Any): Parameter `obj` untuk operasi apply actor audit.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            action (Any): Parameter `action` untuk operasi apply actor audit.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._apply_actor_audit(obj=..., actor=..., action=...)
        """

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
    """Service query/read model untuk workspace analytics dan ringkasan UI.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = AnalyticsQueryService()
    """

    def __init__(
        self,
        report_definition_repository=None,
        report_version_repository=None,
        indicator_definition_repository=None,
        indicator_version_repository=None,
        report_version_indicator_repository=None,
        result_repository=None,
        progress_entry_repository=None,
        dataset_repository=None,
        dataset_version_repository=None,
        dataset_run_repository=None,
    ):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            report_definition_repository (Any): Parameter `report_definition_repository` untuk operasi init.
            report_version_repository (Any): Parameter `report_version_repository` untuk operasi init.
            indicator_definition_repository (Any): Parameter `indicator_definition_repository` untuk operasi init.
            indicator_version_repository (Any): Parameter `indicator_version_repository` untuk operasi init.
            report_version_indicator_repository (Any): Parameter `report_version_indicator_repository` untuk operasi init.
            result_repository (Any): Parameter `result_repository` untuk operasi init.
            progress_entry_repository (Any): Parameter `progress_entry_repository` untuk operasi init.
            dataset_repository (Any): Parameter `dataset_repository` untuk operasi init.
            dataset_version_repository (Any): Parameter `dataset_version_repository` untuk operasi init.
            dataset_run_repository (Any): Parameter `dataset_run_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = AnalyticsQueryService()
        """

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
        self.dataset_repository = dataset_repository or AnalyticsDatasetRepository()
        self.dataset_version_repository = dataset_version_repository or AnalyticsDatasetVersionRepository()
        self.dataset_run_repository = dataset_run_repository or AnalyticsDatasetRunRepository()

    def list_datasets(self):
        """Mengambil daftar dataset analytics untuk workspace UI.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.list_datasets()
        """

        items = []
        for dataset in self.dataset_repository.get_all():
            draft_version = self.dataset_version_repository.get_draft_version(dataset.id)
            published_version = self.dataset_version_repository.get_published_version(dataset.id)
            active_version = draft_version or published_version
            latest_run = None
            if active_version:
                latest_run = self.dataset_run_repository.get_latest_for_dataset_version(active_version.id)
            items.append({
                'dataset': dataset,
                'draft_version': draft_version,
                'published_version': published_version,
                'latest_run': latest_run,
            })
        return items

    def get_dataset_workspace(self, dataset_id):
        """Mengambil ringkasan workspace dataset beserta version dan run terkait.

        Args:
            dataset_id (Any): Primary key internal dataset analytics target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_dataset_workspace(dataset_id=...)
        """

        dataset = self.dataset_repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')

        draft_version = self.dataset_version_repository.get_draft_version(dataset_id)
        published_version = self.dataset_version_repository.get_published_version(dataset_id)
        versions = self.dataset_version_repository.list_versions(dataset_id)
        runs = self.dataset_run_repository.list_by_dataset(dataset_id)

        return {
            'dataset': dataset,
            'draft_version': draft_version,
            'published_version': published_version,
            'versions': versions,
            'runs': runs,
        }

    def list_dataset_runs(self, dataset_id):
        """Mengambil daftar run untuk dataset tertentu.

        Args:
            dataset_id (Any): Primary key internal dataset analytics target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.list_dataset_runs(dataset_id=...)
        """

        dataset = self.dataset_repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')
        return self.dataset_run_repository.list_by_dataset(dataset_id)

    def get_dataset_run_detail(self, run_id):
        """Mengambil detail satu run dataset analytics.

        Args:
            run_id (Any): Primary key internal dataset run target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_dataset_run_detail(run_id=...)
        """

        run = self.dataset_run_repository.get_by_id(run_id)
        if not run:
            raise ValueError('Analytics dataset run tidak ditemukan.')
        return run

    def list_reports(self):
        """Mengambil daftar report analytics.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.list_reports()
        """

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
        """Mengambil workspace report beserta mapping indikatornya.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_report_workspace(report_definition_id=...)
        """

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
        """Mengambil daftar indikator analytics.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.list_indicators()
        """

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
        """Mengambil workspace indikator lengkap dengan result dan progress.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_indicator_workspace(indicator_definition_id=...)
        """

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
        """Mengambil daftar hasil indikator dengan filter periode dan batas row.

        Args:
            indicator_version_id (Any): Primary key internal version indikator target.
            reporting_year (Any): Parameter `reporting_year` untuk operasi list indicator results.
            reporting_period_id (Any): Parameter `reporting_period_id` untuk operasi list indicator results.
            limit (Any): Parameter `limit` untuk operasi list indicator results.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.list_indicator_results(indicator_version_id=..., reporting_year=..., reporting_period_id=...)
        """

        return self.result_repository.list_filtered(
            indicator_version_id=indicator_version_id,
            reporting_year=reporting_year,
            reporting_period_id=reporting_period_id,
            limit=limit,
        )
