"""Service layer domain analytics.

Modul ini mengelola dataset analytics, run dataset, definisi report, indikator, hasil indikator, progress entry, dan query workspace yang dipakai UI maupun API analytics."""

import uuid
from collections import Counter, defaultdict
from datetime import datetime

from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc
from app.modules.form.models import Form
from app.modules.submission.models import Submission

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
    """Service CRUD bisnis untuk dataset analytics dan versi kontraknya.

    Flow domain yang dijaga service ini adalah:
    source operasional -> dataset contract -> publish version -> dataset run -> report.
    Dengan begitu submissions/registry tetap menjadi data mentah, sedangkan report
    membaca dataset yang sudah punya kontrak field, metric, dimension, dan filter.

    Example:
        >>> service = AnalyticsDatasetService()
    """

    ALLOWED_SOURCE_DOMAINS = {
        AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION,
        AnalyticsDataset.SOURCE_DOMAIN_DATA_REGISTRY,
        AnalyticsDataset.SOURCE_DOMAIN_HYBRID,
    }

    ALLOWED_REPORTING_YEAR_MODES = {
        AnalyticsDataset.REPORTING_YEAR_MODE_ACTIVE,
        AnalyticsDataset.REPORTING_YEAR_MODE_EXPLICIT,
        AnalyticsDataset.REPORTING_YEAR_MODE_ALL_TIME,
    }

    ALLOWED_SOURCE_TYPES = {
        AnalyticsDataset.SOURCE_TYPE_SUBMISSION_FACT,
        AnalyticsDataset.SOURCE_TYPE_PUBLISHED_REGISTRY_DIMENSION,
        AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT,
        AnalyticsDataset.SOURCE_TYPE_HYBRID_FACT_DIMENSION,
    }

    ALLOWED_GRAIN_KEYS = {
        AnalyticsDatasetVersion.GRAIN_PER_SUBMISSION,
        AnalyticsDatasetVersion.GRAIN_PER_FORM_PER_YEAR,
        AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR,
        AnalyticsDatasetVersion.GRAIN_PER_REGISTRY_RECORD_PER_YEAR,
    }

    ALLOWED_FRESHNESS_SOURCE_TYPES = {
        AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT,
        AnalyticsDatasetVersion.FRESHNESS_SOURCE_DATA_REGISTRY_MATERIALIZED_AT,
        AnalyticsDatasetVersion.FRESHNESS_SOURCE_HYBRID_WATERMARK,
    }

    ALLOWED_FRESHNESS_STRATEGIES = {
        AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP,
        AnalyticsDatasetVersion.FRESHNESS_STRATEGY_SOURCE_WATERMARK_COMPARE,
        AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MANUAL_ASSERTION,
    }

    def __init__(self, dataset_repository=None, dataset_version_repository=None):
        """Inisialisasi class beserta dependency yang diperlukan."""

        super().__init__(repository=dataset_repository or AnalyticsDatasetRepository())
        self.version_repository = dataset_version_repository or AnalyticsDatasetVersionRepository()

    def create_dataset_bundle(self, data, actor=None):
        """Membuat dataset beserta draft contract awal dalam satu operasi.

        Endpoint UI create dataset lebih nyaman bila identitas dataset, source picker,
        dan contract field langsung tersimpan sebagai satu paket. Method ini membuat
        definition dataset lalu otomatis menyiapkan draft version pertamanya.
        """

        dataset_payload = self._extract_dataset_payload(data)
        version_payload = self._extract_version_payload(data, dataset_payload=dataset_payload)
        dataset = self.create_dataset(dataset_payload, actor=actor)
        draft_version = self.create_dataset_version(dataset.id, version_payload, actor=actor)
        return {
            'dataset': dataset,
            'draft_version': draft_version,
        }

    def update_dataset_bundle(self, dataset_id, data, actor=None):
        """Memperbarui definition dataset dan meng-upsert draft contract aktif.

        Bila draft version sudah ada, ia di-update di tempat. Bila belum ada
        (misalnya dataset sudah punya version published saja), method ini akan
        membuat draft version baru agar perubahan contract tidak menimpa histori
        published sebelumnya.
        """

        dataset_payload = self._extract_dataset_payload(data)
        version_payload = self._extract_version_payload(data, dataset_payload=dataset_payload)
        dataset = self.update_dataset(dataset_id, dataset_payload, actor=actor)
        draft_version = self.upsert_draft_version(dataset_id, version_payload, actor=actor)
        return {
            'dataset': dataset,
            'draft_version': draft_version,
        }

    def create_dataset(self, data, actor=None):
        """Membuat definisi dataset analytics baru."""

        normalized = self._normalize_dataset_payload(data)
        self._ensure_dataset_key_available(normalized['dataset_key'])

        dataset = AnalyticsDataset(
            uuid=str(uuid.uuid4()),
            dataset_key=normalized['dataset_key'],
            name=normalized['name'],
            description=normalized['description'],
            source_domain=normalized['source_domain'],
            source_type=normalized['source_type'],
            primary_source_ref=normalized['primary_source_ref'],
            status=normalized['status'],
            is_active=normalized['is_active'],
            is_year_scoped=normalized['is_year_scoped'],
            default_reporting_year_mode=normalized['default_reporting_year_mode'],
            owner_scope_type=normalized['owner_scope_type'],
            owner_scope_code=normalized['owner_scope_code'],
            owner_scope_name=normalized['owner_scope_name'],
            owner_scope_path=normalized['owner_scope_path'],
            settings_json=normalized['settings_json'],
            tags_json=normalized['tags_json'],
        )
        self._apply_actor_audit(dataset, actor, action='create')
        return self.repository.save(dataset)

    def update_dataset(self, dataset_id, data, actor=None):
        """Memperbarui metadata definition dataset analytics."""

        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')

        normalized = self._normalize_dataset_payload(data, existing_dataset=dataset)
        self._ensure_dataset_key_available(normalized['dataset_key'], ignore_dataset_id=dataset_id)

        dataset.dataset_key = normalized['dataset_key']
        dataset.name = normalized['name']
        dataset.description = normalized['description']
        dataset.source_domain = normalized['source_domain']
        dataset.source_type = normalized['source_type']
        dataset.primary_source_ref = normalized['primary_source_ref']
        dataset.status = normalized['status']
        dataset.is_active = normalized['is_active']
        dataset.is_year_scoped = normalized['is_year_scoped']
        dataset.default_reporting_year_mode = normalized['default_reporting_year_mode']
        dataset.owner_scope_type = normalized['owner_scope_type']
        dataset.owner_scope_code = normalized['owner_scope_code']
        dataset.owner_scope_name = normalized['owner_scope_name']
        dataset.owner_scope_path = normalized['owner_scope_path']
        dataset.settings_json = normalized['settings_json']
        dataset.tags_json = normalized['tags_json']
        self._apply_actor_audit(dataset, actor, action='update')
        return self.repository.save(dataset)

    def create_dataset_version(self, dataset_id, data, actor=None):
        """Membuat version dataset analytics baru."""

        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')

        normalized = self._normalize_dataset_version_payload(dataset, data)
        version = AnalyticsDatasetVersion(
            uuid=str(uuid.uuid4()),
            dataset_id=dataset_id,
            version_number=self.version_repository.get_next_version_number(dataset_id),
            status=normalized['status'],
            is_current_draft=normalized['is_current_draft'],
            is_current_published=normalized['is_current_published'],
            source_contract_json=normalized['source_contract_json'],
            query_spec_json=normalized['query_spec_json'],
            transform_spec_json=normalized['transform_spec_json'],
            join_registry_spec_json=normalized['join_registry_spec_json'],
            grain_key=normalized['grain_key'],
            output_schema_json=normalized['output_schema_json'],
            dimension_definitions_json=normalized['dimension_definitions_json'],
            metric_definitions_json=normalized['metric_definitions_json'],
            default_filters_json=normalized['default_filters_json'],
            sort_spec_json=normalized['sort_spec_json'],
            freshness_source_type=normalized['freshness_source_type'],
            freshness_source_ref=normalized['freshness_source_ref'],
            freshness_strategy=normalized['freshness_strategy'],
            freshness_policy_json=normalized['freshness_policy_json'],
            publish_notes=normalized['publish_notes'],
            published_at=normalized['published_at'],
        )
        self._apply_actor_audit(version, actor, action='create')
        return self.version_repository.save(version)

    def upsert_draft_version(self, dataset_id, data, actor=None):
        """Membuat atau memperbarui current draft version untuk dataset tertentu."""

        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan.')

        normalized = self._normalize_dataset_version_payload(dataset, data)
        draft_version = self.version_repository.get_draft_version(dataset_id)
        if not draft_version:
            return self.create_dataset_version(dataset_id, normalized, actor=actor)

        draft_version.status = AnalyticsDatasetVersion.STATUS_DRAFT
        draft_version.is_current_draft = True
        draft_version.is_current_published = False
        draft_version.source_contract_json = normalized['source_contract_json']
        draft_version.query_spec_json = normalized['query_spec_json']
        draft_version.transform_spec_json = normalized['transform_spec_json']
        draft_version.join_registry_spec_json = normalized['join_registry_spec_json']
        draft_version.grain_key = normalized['grain_key']
        draft_version.output_schema_json = normalized['output_schema_json']
        draft_version.dimension_definitions_json = normalized['dimension_definitions_json']
        draft_version.metric_definitions_json = normalized['metric_definitions_json']
        draft_version.default_filters_json = normalized['default_filters_json']
        draft_version.sort_spec_json = normalized['sort_spec_json']
        draft_version.freshness_source_type = normalized['freshness_source_type']
        draft_version.freshness_source_ref = normalized['freshness_source_ref']
        draft_version.freshness_strategy = normalized['freshness_strategy']
        draft_version.freshness_policy_json = normalized['freshness_policy_json']
        draft_version.publish_notes = normalized['publish_notes']
        self._apply_actor_audit(draft_version, actor, action='update')
        return self.version_repository.save(draft_version)

    def publish_dataset_version(self, version_id, actor=None):
        """Mempublish dataset version dan mengarsipkan version published lain."""

        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ValueError('Analytics dataset version tidak ditemukan.')

        if not self._has_contract_content(version):
            raise ValueError('Analytics dataset version belum memiliki contract field/dimension/metric yang siap dipublish.')

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

    def _extract_dataset_payload(self, data):
        return dict((data or {}).get('dataset') or data or {})

    def _extract_version_payload(self, data, dataset_payload=None):
        dataset_payload = dataset_payload or {}
        version_payload = dict((data or {}).get('draft_version') or {})
        if version_payload:
            return version_payload

        return {
            'source_contract_json': (data or {}).get('source_contract_json'),
            'query_spec_json': (data or {}).get('query_spec_json'),
            'transform_spec_json': (data or {}).get('transform_spec_json'),
            'join_registry_spec_json': (data or {}).get('join_registry_spec_json'),
            'grain_key': (data or {}).get('grain_key'),
            'output_schema_json': (data or {}).get('output_schema_json'),
            'dimension_definitions_json': (data or {}).get('dimension_definitions_json'),
            'metric_definitions_json': (data or {}).get('metric_definitions_json'),
            'default_filters_json': (data or {}).get('default_filters_json'),
            'sort_spec_json': (data or {}).get('sort_spec_json'),
            'freshness_source_type': (data or {}).get('freshness_source_type'),
            'freshness_source_ref': (data or {}).get('freshness_source_ref'),
            'freshness_strategy': (data or {}).get('freshness_strategy'),
            'freshness_policy_json': (data or {}).get('freshness_policy_json'),
            'publish_notes': (data or {}).get('publish_notes'),
            'source_domain': dataset_payload.get('source_domain'),
            'source_type': dataset_payload.get('source_type'),
            'primary_source_ref': dataset_payload.get('primary_source_ref'),
        }

    def _normalize_dataset_payload(self, data, existing_dataset=None):
        data = data or {}
        dataset_key = (data.get('dataset_key') or getattr(existing_dataset, 'dataset_key', None) or '').strip()
        if not dataset_key:
            raise ValueError('dataset_key wajib diisi untuk analytics dataset.')

        source_domain = data.get('source_domain') or getattr(existing_dataset, 'source_domain', None) or AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION
        if source_domain not in self.ALLOWED_SOURCE_DOMAINS:
            raise ValueError('source_domain analytics dataset tidak valid.')

        source_type = data.get('source_type') or getattr(existing_dataset, 'source_type', None)
        if not source_type:
            source_type = self._default_source_type_for_domain(source_domain)
        if source_type not in self.ALLOWED_SOURCE_TYPES:
            raise ValueError('source_type analytics dataset tidak valid.')

        reporting_year_mode = (
            data.get('default_reporting_year_mode')
            or getattr(existing_dataset, 'default_reporting_year_mode', None)
            or AnalyticsDataset.REPORTING_YEAR_MODE_ACTIVE
        )
        if reporting_year_mode not in self.ALLOWED_REPORTING_YEAR_MODES:
            raise ValueError('default_reporting_year_mode analytics dataset tidak valid.')

        settings_json = self._coerce_dict(data.get('settings_json'), getattr(existing_dataset, 'settings_json', None) or {})
        settings_json = {
            **settings_json,
            'report_family': data.get('report_family', settings_json.get('report_family')),
            'report_meta_description': data.get('report_meta_description', settings_json.get('report_meta_description')),
            'report_builder_notes': data.get('report_builder_notes', settings_json.get('report_builder_notes')),
            'preferred_visualizations': self._coerce_list(
                data.get('preferred_visualizations', settings_json.get('preferred_visualizations'))
            ),
            'supported_period_modes': self._coerce_list(
                data.get('supported_period_modes', settings_json.get('supported_period_modes'))
            ),
            'suggested_report_blocks': self._coerce_list(
                data.get('suggested_report_blocks', settings_json.get('suggested_report_blocks'))
            ),
        }

        return {
            'dataset_key': dataset_key,
            'name': (data.get('name') or getattr(existing_dataset, 'name', None) or dataset_key).strip(),
            'description': data.get('description', getattr(existing_dataset, 'description', None)),
            'source_domain': source_domain,
            'source_type': source_type,
            'primary_source_ref': data.get('primary_source_ref', getattr(existing_dataset, 'primary_source_ref', None)),
            'status': data.get('status', getattr(existing_dataset, 'status', None) or AnalyticsDataset.STATUS_DRAFT),
            'is_active': data.get('is_active', getattr(existing_dataset, 'is_active', True)),
            'is_year_scoped': data.get('is_year_scoped', getattr(existing_dataset, 'is_year_scoped', True)),
            'default_reporting_year_mode': reporting_year_mode,
            'owner_scope_type': data.get('owner_scope_type', getattr(existing_dataset, 'owner_scope_type', None)),
            'owner_scope_code': data.get('owner_scope_code', getattr(existing_dataset, 'owner_scope_code', None)),
            'owner_scope_name': data.get('owner_scope_name', getattr(existing_dataset, 'owner_scope_name', None)),
            'owner_scope_path': self._coerce_list(data.get('owner_scope_path', getattr(existing_dataset, 'owner_scope_path', []))),
            'settings_json': settings_json,
            'tags_json': self._coerce_list(data.get('tags_json', getattr(existing_dataset, 'tags_json', []))),
        }

    def _normalize_dataset_version_payload(self, dataset, data):
        data = data or {}
        source_contract_json = self._coerce_dict(data.get('source_contract_json'), {})
        source_contract_json = {
            **source_contract_json,
            'source_domain': data.get('source_domain', source_contract_json.get('source_domain', dataset.source_domain)),
            'source_type': data.get('source_type', source_contract_json.get('source_type', dataset.source_type)),
            'primary_source_ref': data.get('primary_source_ref', source_contract_json.get('primary_source_ref', dataset.primary_source_ref)),
            'selected_fields': self._coerce_list(data.get('selected_fields', source_contract_json.get('selected_fields'))),
            'submission_refs': self._coerce_list(data.get('submission_refs', source_contract_json.get('submission_refs'))),
            'registry_refs': self._coerce_list(data.get('registry_refs', source_contract_json.get('registry_refs'))),
            'source_field_map': self._coerce_dict(data.get('source_field_map'), source_contract_json.get('source_field_map') or {}),
        }
        if not source_contract_json['selected_fields']:
            source_contract_json['selected_fields'] = self._infer_selected_fields(source_contract_json, data)
        if not source_contract_json['selected_fields']:
            raise ValueError('Analytics dataset draft wajib memiliki selected_fields minimal satu field sumber.')

        grain_key = data.get('grain_key') or AnalyticsDatasetVersion.GRAIN_PER_SCOPE_PER_YEAR
        if grain_key not in self.ALLOWED_GRAIN_KEYS:
            raise ValueError('grain_key analytics dataset tidak valid.')

        freshness_source_type = (
            data.get('freshness_source_type')
            or self._default_freshness_source_type(dataset.source_domain)
        )
        if freshness_source_type not in self.ALLOWED_FRESHNESS_SOURCE_TYPES:
            raise ValueError('freshness_source_type analytics dataset tidak valid.')

        freshness_strategy = data.get('freshness_strategy') or AnalyticsDatasetVersion.FRESHNESS_STRATEGY_MAX_TIMESTAMP
        if freshness_strategy not in self.ALLOWED_FRESHNESS_STRATEGIES:
            raise ValueError('freshness_strategy analytics dataset tidak valid.')

        dimension_definitions_json = self._coerce_list(data.get('dimension_definitions_json'))
        metric_definitions_json = self._coerce_list(data.get('metric_definitions_json'))
        if not metric_definitions_json:
            metric_definitions_json = self._infer_metric_definitions(data)
        output_schema_json = self._coerce_list(data.get('output_schema_json'))
        if not output_schema_json:
            output_schema_json = dimension_definitions_json + metric_definitions_json
        if not metric_definitions_json:
            raise ValueError('Analytics dataset draft wajib memiliki metric_definitions_json minimal satu metric.')

        return {
            'status': data.get('status', AnalyticsDatasetVersion.STATUS_DRAFT),
            'is_current_draft': data.get('is_current_draft', True),
            'is_current_published': data.get('is_current_published', False),
            'source_contract_json': source_contract_json,
            'query_spec_json': self._coerce_dict(data.get('query_spec_json'), {}),
            'transform_spec_json': self._coerce_dict(data.get('transform_spec_json'), {}),
            'join_registry_spec_json': self._coerce_list(data.get('join_registry_spec_json')),
            'grain_key': grain_key,
            'output_schema_json': output_schema_json,
            'dimension_definitions_json': dimension_definitions_json,
            'metric_definitions_json': metric_definitions_json,
            'default_filters_json': self._coerce_dict(data.get('default_filters_json'), {}),
            'sort_spec_json': self._coerce_list(data.get('sort_spec_json')),
            'freshness_source_type': freshness_source_type,
            'freshness_source_ref': data.get('freshness_source_ref'),
            'freshness_strategy': freshness_strategy,
            'freshness_policy_json': self._coerce_dict(data.get('freshness_policy_json'), {}),
            'publish_notes': data.get('publish_notes'),
            'published_at': data.get('published_at'),
        }

    def _ensure_dataset_key_available(self, dataset_key, ignore_dataset_id=None):
        existing = self.repository.get_by_key(dataset_key)
        if existing and getattr(existing, 'id', None) != ignore_dataset_id:
            raise ValueError('dataset_key analytics dataset sudah dipakai oleh dataset lain.')

    def _default_source_type_for_domain(self, source_domain):
        if source_domain == AnalyticsDataset.SOURCE_DOMAIN_DATA_REGISTRY:
            return AnalyticsDataset.SOURCE_TYPE_PUBLISHED_REGISTRY_DIMENSION
        if source_domain == AnalyticsDataset.SOURCE_DOMAIN_HYBRID:
            return AnalyticsDataset.SOURCE_TYPE_HYBRID_FACT_DIMENSION
        return AnalyticsDataset.SOURCE_TYPE_AGGREGATED_SUBMISSION_FACT

    def _default_freshness_source_type(self, source_domain):
        if source_domain == AnalyticsDataset.SOURCE_DOMAIN_DATA_REGISTRY:
            return AnalyticsDatasetVersion.FRESHNESS_SOURCE_DATA_REGISTRY_MATERIALIZED_AT
        if source_domain == AnalyticsDataset.SOURCE_DOMAIN_HYBRID:
            return AnalyticsDatasetVersion.FRESHNESS_SOURCE_HYBRID_WATERMARK
        return AnalyticsDatasetVersion.FRESHNESS_SOURCE_SUBMISSIONS_SUBMITTED_AT

    def _infer_selected_fields(self, source_contract_json, data):
        inferred_fields = []

        for item in self._coerce_list(data.get('output_schema_json')):
            if isinstance(item, dict) and item.get('key'):
                inferred_fields.append(item.get('key'))

        for item in self._coerce_list(data.get('dimension_definitions_json')):
            if isinstance(item, dict) and item.get('key'):
                inferred_fields.append(item.get('key'))

        for item in self._coerce_list(data.get('metric_definitions_json')):
            if isinstance(item, dict) and item.get('key'):
                inferred_fields.append(item.get('key'))

        if source_contract_json.get('source_field_map'):
            inferred_fields.extend(list(source_contract_json['source_field_map'].keys()))

        if not inferred_fields:
            inferred_fields.extend(
                key for key in source_contract_json.keys()
                if key not in {'source_domain', 'source_type', 'primary_source_ref', 'selected_fields', 'submission_refs', 'registry_refs', 'source_field_map'}
            )

        seen = set()
        normalized_fields = []
        for item in inferred_fields:
            if item and item not in seen:
                seen.add(item)
                normalized_fields.append(item)
        return normalized_fields

    def _infer_metric_definitions(self, data):
        inferred_metrics = []
        query_spec = self._coerce_dict(data.get('query_spec_json'), {})

        for item in self._coerce_list(data.get('output_schema_json')):
            if isinstance(item, dict) and item.get('key'):
                inferred_metrics.append({'key': item.get('key')})

        for item in self._coerce_list(query_spec.get('select')):
            if isinstance(item, dict) and item.get('key'):
                inferred_metrics.append({'key': item.get('key')})
            elif isinstance(item, str) and item.strip():
                raw_key = item.split(' as ')[-1].split(' AS ')[-1].strip()
                normalized_key = raw_key.replace('count(*)', 'count').replace('(', '_').replace(')', '').replace('*', 'all').replace(' ', '_')
                inferred_metrics.append({'key': normalized_key or 'metric_auto'})

        seen = set()
        normalized_metrics = []
        for item in inferred_metrics:
            key = item.get('key') if isinstance(item, dict) else None
            if key and key not in seen:
                seen.add(key)
                normalized_metrics.append({'key': key})
        return normalized_metrics

    def _has_contract_content(self, version):
        return bool(
            getattr(version, 'source_contract_json', None)
            and getattr(version, 'metric_definitions_json', None)
            and getattr(version, 'output_schema_json', None)
        )

    def _coerce_list(self, value):
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    def _coerce_dict(self, value, default=None):
        if value is None:
            return dict(default or {})
        if isinstance(value, dict):
            return dict(value)
        raise ValueError('Payload JSON analytics dataset harus berbentuk object/dict.')

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        """Helper internal untuk apply actor audit."""

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
        if run.started_at and run.finished_at:
            run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
        run.freshness_status = data.get('freshness_status', run.freshness_status or AnalyticsDatasetRun.FRESHNESS_UNKNOWN)
        run.source_watermark = data.get('source_watermark')
        run.source_snapshot_json = data.get('source_snapshot_json') or run.source_snapshot_json or {}
        run.freshness_evaluated_at = data.get('freshness_evaluated_at') or now_utc()
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
        if run.started_at and run.finished_at:
            run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
        run.freshness_status = data.get('freshness_status', AnalyticsDatasetRun.FRESHNESS_FAILED)
        run.source_snapshot_json = data.get('source_snapshot_json') or run.source_snapshot_json or {}
        run.freshness_evaluated_at = data.get('freshness_evaluated_at') or now_utc()
        run.error_code = data.get('error_code')
        run.error_message = data.get('error_message')
        run.error_detail_json = data.get('error_detail_json') or {}
        self._apply_actor_audit(run, actor, action='update')
        return self.repository.save(run)

    def execute_run(self, dataset_id, dataset_version_id, data=None, actor=None):
        """Menjalankan dataset run end-to-end agar UI bisa langsung menampilkan hasil analytics.

        Method ini dipakai oleh layer web/API sebagai jembatan eksplisit antara
        source data operasional (mis. form submission) dengan materialisasi dataset
        analytics. Saat ini engine sinkron ini memprioritaskan source bertipe
        submission fact/agregat sehingga setelah user kirim form, data dapat
        dijalankan menjadi dataset run dan langsung dipakai detail report.

        Args:
            dataset_id (Any): Primary key internal dataset analytics target.
            dataset_version_id (Any): Primary key internal dataset version target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity run dengan status succeeded atau failed.
        """

        run = self.start_run(dataset_id, dataset_version_id, data=data, actor=actor)

        try:
            materialized = self._materialize_run_payload(run)
            return self.complete_run(run.id, materialized, actor=actor)
        except Exception as error:
            db.session.rollback()
            return self.fail_run(
                run.id,
                {
                    'error_code': 'DATASET_RUN_EXECUTION_FAILED',
                    'error_message': str(error),
                    'error_detail_json': {
                        'dataset_id': dataset_id,
                        'dataset_version_id': dataset_version_id,
                    },
                },
                actor=actor,
            )

    def _materialize_run_payload(self, run):
        """Membentuk payload hasil run sinkron berdasarkan kontrak dataset aktif."""

        dataset = getattr(run, 'dataset', None) or self.dataset_repository.get_by_id(run.dataset_id)
        dataset_version = getattr(run, 'dataset_version', None) or self.dataset_version_repository.get_by_id(run.dataset_version_id)

        if not dataset:
            raise ValueError('Analytics dataset tidak ditemukan saat eksekusi run.')
        if not dataset_version:
            raise ValueError('Analytics dataset version tidak ditemukan saat eksekusi run.')

        if dataset.source_domain != AnalyticsDataset.SOURCE_DOMAIN_SUBMISSION:
            raise ValueError('Engine run sinkron saat ini baru mendukung dataset source_domain submission.')

        rows, source_snapshot = self._load_submission_rows(dataset, dataset_version, run)
        summary = self._build_submission_summary(rows, run, dataset, dataset_version, source_snapshot)
        source_watermark = source_snapshot.get('latest_submitted_at')
        freshness_status = AnalyticsDatasetRun.FRESHNESS_FRESH if rows else AnalyticsDatasetRun.FRESHNESS_STALE

        return {
            'freshness_status': freshness_status,
            'source_watermark': source_watermark,
            'source_snapshot_json': source_snapshot,
            'freshness_evaluated_at': now_utc(),
            'result_row_count': len(rows),
            'result_schema_json': dataset_version.output_schema_json or self._infer_result_schema(rows),
            'result_preview_json': rows[:10],
            'materialization_ref': f'analytics://dataset-runs/{run.id}',
            'summary_json': summary,
        }

    def _load_submission_rows(self, dataset, dataset_version, run):
        """Mengambil row snapshot dari submission berdasarkan kontrak dataset."""

        source_contract = getattr(dataset_version, 'source_contract_json', None) or {}
        settings_json = getattr(dataset, 'settings_json', None) or {}
        requested_filters = getattr(run, 'requested_filters_json', None) or {}
        form_refs = self._resolve_dataset_form_refs(dataset, dataset_version)
        forms = self._resolve_forms(form_refs)

        if not forms:
            raise ValueError('Dataset belum terhubung ke form submission secara eksplisit. Tambahkan form_code/form_slug/form_id pada source contract atau settings dataset.')

        form_ids = [form.id for form in forms]
        requested_reporting_year = run.requested_reporting_year or requested_filters.get('reporting_year') or source_contract.get('reporting_year')

        query = Submission.query.filter(
            Submission.deleted_at.is_(None),
            Submission.form_id.in_(form_ids),
            Submission.status == 'submitted',
        )

        if requested_reporting_year:
            query = query.filter(Submission.reporting_year == requested_reporting_year)

        source_type = requested_filters.get('source_type') or source_contract.get('source_type') or settings_json.get('source_type')
        if source_type:
            query = query.filter(Submission.source_type == source_type)

        submissions = query.order_by(Submission.submitted_at.asc(), Submission.id.asc()).all()
        rows = [
            self._build_submission_row_snapshot(submission, dataset_version)
            for submission in submissions
        ]

        source_snapshot = {
            'form_ids': form_ids,
            'form_codes': [getattr(form, 'code', None) for form in forms],
            'form_slugs': [getattr(form, 'slug', None) for form in forms],
            'requested_reporting_year': requested_reporting_year,
            'requested_filters_json': requested_filters,
            'submission_count': len(submissions),
            'latest_submitted_at': submissions[-1].submitted_at.isoformat() if submissions and submissions[-1].submitted_at else None,
        }

        return rows, source_snapshot

    def _resolve_dataset_form_refs(self, dataset, dataset_version):
        """Menggabungkan referensi form eksplisit dari dataset/settings/source contract."""

        refs = []
        for payload in (
            getattr(dataset, 'settings_json', None) or {},
            getattr(dataset_version, 'source_contract_json', None) or {},
        ):
            refs.extend(self._coerce_list(payload.get('form_ids')))
            refs.extend(self._coerce_list(payload.get('form_codes')))
            refs.extend(self._coerce_list(payload.get('form_slugs')))
            refs.extend(self._coerce_list(payload.get('form_refs')))
            for key in ('form_id', 'form_code', 'form_slug'):
                value = payload.get(key)
                if value not in (None, ''):
                    refs.append(value)

        primary_ref = getattr(dataset, 'primary_source_ref', None)
        if primary_ref not in (None, ''):
            refs.append(primary_ref)

        unique_refs = []
        seen = set()
        for ref in refs:
            normalized = str(ref).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_refs.append(ref)
        return unique_refs

    def _resolve_forms(self, refs):
        """Mengubah daftar ref menjadi entity Form unik."""

        forms = []
        seen_ids = set()
        for ref in refs:
            form = None
            if isinstance(ref, int) or (isinstance(ref, str) and str(ref).isdigit()):
                form = Form.query.filter(Form.deleted_at.is_(None), Form.id == int(ref)).first()
            if not form:
                text_ref = str(ref).strip()
                form = Form.query.filter(
                    Form.deleted_at.is_(None),
                    db.or_(Form.code == text_ref, Form.slug == text_ref, Form.uuid == text_ref),
                ).first()
            if form and form.id not in seen_ids:
                seen_ids.add(form.id)
                forms.append(form)
        return forms

    def _build_submission_row_snapshot(self, submission, dataset_version):
        """Membentuk row snapshot analytics dari satu submission."""

        payload = dict(getattr(submission, 'payload', None) or {})
        date_field = self._resolve_date_field(payload, dataset_version)
        normalized_date = self._normalize_date_value(payload.get(date_field)) if date_field else None
        reporting_year = normalized_date.year if normalized_date else submission.reporting_year
        quarter_number = ((normalized_date.month - 1) // 3 + 1) if normalized_date else 1
        semester_number = 1 if (not normalized_date or normalized_date.month <= 6) else 2

        row = {
            'submission_id': submission.id,
            'submission_uuid': submission.uuid,
            'submission_number': submission.submission_number,
            'form_id': submission.form_id,
            'form_version_id': submission.form_version_id,
            'reporting_year': reporting_year,
            'reporting_period_id': submission.reporting_period_id,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'owner_scope_code': submission.owner_scope_code,
            'owner_scope_name': submission.owner_scope_name,
            'subject_ref_code': submission.subject_ref_code,
            'subject_ref_name': submission.subject_ref_name,
            **payload,
        }

        row['tanggal'] = normalized_date.isoformat() if normalized_date else payload.get(date_field or 'tanggal')
        row['quarter_number'] = quarter_number
        row['quarter_label'] = f'{reporting_year}-Q{quarter_number}'
        row['semester_number'] = semester_number
        row['semester_label'] = f'{reporting_year}-S{semester_number}'
        row['year_label'] = str(reporting_year)
        row['hasil'] = row.get('hasil') or row.get('status_label') or row.get('status') or 'Tanpa Status'
        row['jenis'] = row.get('jenis') or row.get('category') or row.get('kategori') or 'Tanpa Jenis'
        row['daerah'] = row.get('daerah') or row.get('wilayah') or row.get('owner_scope_name') or 'Tanpa Daerah'
        return row

    def _build_submission_summary(self, rows, run, dataset, dataset_version, source_snapshot):
        """Menyusun summary human-friendly untuk detail report analytics."""

        hasil_counter = Counter()
        jenis_counter = Counter()
        daerah_counter = Counter()
        yearly_periods = defaultdict(lambda: {'label': None, 'period_type': 'yearly', 'period_number': 1, 'reporting_year': None, 'total': 0, 'selesai': 0, 'dikembalikan': 0})
        semester_periods = defaultdict(lambda: {'label': None, 'period_type': 'semesterly', 'period_number': None, 'reporting_year': None, 'total': 0, 'selesai': 0, 'dikembalikan': 0})
        quarterly_periods = defaultdict(lambda: {'label': None, 'period_type': 'quarterly', 'period_number': None, 'reporting_year': None, 'total': 0, 'selesai': 0, 'dikembalikan': 0})

        for row in rows:
            hasil = row.get('hasil') or 'Tanpa Status'
            jenis = row.get('jenis') or 'Tanpa Jenis'
            daerah = row.get('daerah') or 'Tanpa Daerah'
            hasil_counter[hasil] += 1
            jenis_counter[jenis] += 1
            daerah_counter[daerah] += 1

            reporting_year = row.get('reporting_year')
            semester_label = row.get('semester_label') or f'{reporting_year}-S1'
            quarter_label = row.get('quarter_label') or f'{reporting_year}-Q1'
            semester_number = row.get('semester_number') or 1
            quarter_number = row.get('quarter_number') or 1
            year_label = row.get('year_label') or str(reporting_year)

            for bucket, label, period_type, period_number in (
                (yearly_periods[year_label], year_label, 'yearly', 1),
                (semester_periods[semester_label], semester_label, 'semesterly', semester_number),
                (quarterly_periods[quarter_label], quarter_label, 'quarterly', quarter_number),
            ):
                bucket['label'] = label
                bucket['period_type'] = period_type
                bucket['period_number'] = period_number
                bucket['reporting_year'] = reporting_year
                bucket['total'] += 1
                if str(hasil).lower() == 'selesai':
                    bucket['selesai'] += 1
                if str(hasil).lower() == 'dikembalikan':
                    bucket['dikembalikan'] += 1

        selesai_count = sum(1 for row in rows if str(row.get('hasil') or '').lower() == 'selesai')
        dikembalikan_count = sum(1 for row in rows if str(row.get('hasil') or '').lower() == 'dikembalikan')
        row_dates = [row.get('tanggal') for row in rows if row.get('tanggal')]

        return {
            'dataset_key': dataset.dataset_key,
            'dataset_version_number': getattr(dataset_version, 'version_number', None),
            'requested_reporting_year': run.requested_reporting_year,
            'row_count': len(rows),
            'date_min': min(row_dates) if row_dates else None,
            'date_max': max(row_dates) if row_dates else None,
            'hasil_counts': dict(hasil_counter),
            'jenis_counts': dict(jenis_counter),
            'top_daerah': [
                {'label': label, 'count': count}
                for label, count in daerah_counter.most_common(10)
            ],
            'completion': {
                'selesai': selesai_count,
                'dikembalikan': dikembalikan_count,
                'achievement_percentage': round((selesai_count / len(rows)) * 100, 2) if rows else 0,
            },
            'filter_dimensions': {
                'reporting_years': sorted({row.get('reporting_year') for row in rows if row.get('reporting_year') is not None}),
                'hasil_options': sorted({row.get('hasil') for row in rows if row.get('hasil')}),
                'jenis_options': sorted({row.get('jenis') for row in rows if row.get('jenis')}),
            },
            'period_metrics': {
                'yearly': self._serialize_period_metrics(yearly_periods),
                'semesterly': self._serialize_period_metrics(semester_periods),
                'quarterly': self._serialize_period_metrics(quarterly_periods),
            },
            'row_snapshots': rows,
            'source_snapshot': source_snapshot,
        }

    def _serialize_period_metrics(self, periods):
        """Menormalisasi bucket periode agar siap dipakai chart/report."""

        serialized = []
        for item in periods.values():
            total = item['total']
            serialized.append({
                **item,
                'achievement_percentage': round((item['selesai'] / total) * 100, 2) if total else 0,
            })
        return sorted(serialized, key=lambda item: (item['reporting_year'] or 0, item['period_number'] or 0, item['label'] or ''))

    def _infer_result_schema(self, rows):
        """Membuat schema preview sederhana bila output schema belum didefinisikan."""

        if not rows:
            return []
        first_row = rows[0]
        schema = []
        for key, value in first_row.items():
            value_type = 'string'
            if isinstance(value, bool):
                value_type = 'boolean'
            elif isinstance(value, int):
                value_type = 'integer'
            elif isinstance(value, float):
                value_type = 'number'
            schema.append({'key': key, 'type': value_type})
        return schema

    def _resolve_date_field(self, payload, dataset_version):
        """Menentukan field tanggal dari payload berdasarkan kontrak atau nama umum."""

        source_contract = getattr(dataset_version, 'source_contract_json', None) or {}
        transform_spec = getattr(dataset_version, 'transform_spec_json', None) or {}
        candidates = [
            source_contract.get('date_field'),
            transform_spec.get('date_field'),
            'tanggal',
            'submitted_at',
            'date',
            'datetime',
        ]
        for candidate in candidates:
            if candidate and candidate in payload:
                return candidate
        return None

    def _normalize_date_value(self, value):
        """Mengubah berbagai bentuk nilai tanggal menjadi object date bila memungkinkan."""

        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
            return value

        text_value = str(value).strip()
        if not text_value:
            return None
        normalized = text_value.replace('Z', '+00:00')
        try:
            if 'T' in normalized:
                return datetime.fromisoformat(normalized).date()
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            try:
                return datetime.strptime(normalized[:10], '%Y-%m-%d').date()
            except ValueError:
                return None

    def _coerce_list(self, value):
        """Mengubah scalar/list menjadi list untuk memudahkan normalisasi input kontrak."""

        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

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
    """Service pengelolaan definisi report analytics dan versi semi-CMS-nya.

    Report diperlakukan sebagai layer semi-CMS yang membaca kontrak dataset
    terkurasi, bukan source mentah langsung. Karena itu service ini menjaga
    boundary dataset -> report dengan relasi eksplisit ke dataset dan dataset
    version aktif.
    """

    DEFAULT_REPORT_BLOCKS = [
        'metric_cards',
        'plotly_timeseries',
        'detail_table',
        'narrative',
    ]
    DEFAULT_PERIOD_PRESETS = [
        'current_quarter',
        'current_semester',
        'current_year',
    ]
    REPORT_TYPE_ALIASES = {
        'custom_report': AnalyticsReportDefinition.TYPE_CUSTOM,
        'performance_report': AnalyticsReportDefinition.TYPE_SCORECARD,
        'narrative_report': AnalyticsReportDefinition.TYPE_MONITORING,
        'geo_report': AnalyticsReportDefinition.TYPE_MONITORING,
    }
    ALLOWED_REPORT_TYPES = {
        AnalyticsReportDefinition.TYPE_PK,
        AnalyticsReportDefinition.TYPE_RENAKSI,
        AnalyticsReportDefinition.TYPE_SCORECARD,
        AnalyticsReportDefinition.TYPE_MONITORING,
        AnalyticsReportDefinition.TYPE_CUSTOM,
    }
    REPORT_FAMILY_DEFAULTS = {
        'custom': {
            'blocks': ['metric_cards', 'plotly_timeseries', 'detail_table', 'narrative'],
            'supported_period_modes': ['quarterly', 'semester', 'yearly'],
            'quick_presets': ['current_quarter', 'current_semester', 'current_year'],
            'layout': {'viewer_variant': 'semi_cms'},
        },
        'pk': {
            'blocks': ['metric_cards', 'detail_table', 'plotly_timeseries', 'narrative'],
            'supported_period_modes': ['quarterly', 'semester', 'yearly'],
            'quick_presets': ['current_quarter', 'current_semester', 'current_year'],
            'layout': {'viewer_variant': 'pk_summary'},
        },
        'ik': {
            'blocks': ['metric_cards', 'detail_table', 'narrative'],
            'supported_period_modes': ['monthly', 'quarterly', 'yearly'],
            'quick_presets': ['current_month', 'current_quarter', 'current_year'],
            'layout': {'viewer_variant': 'ik_summary'},
        },
        'renaksi': {
            'blocks': ['metric_cards', 'detail_table', 'narrative'],
            'supported_period_modes': ['monthly', 'quarterly', 'yearly'],
            'quick_presets': ['current_month', 'current_quarter', 'current_year'],
            'layout': {'viewer_variant': 'renaksi_progress'},
        },
        'dashboard-eksekutif': {
            'blocks': ['metric_cards', 'plotly_timeseries', 'geo_map', 'detail_table', 'narrative'],
            'supported_period_modes': ['monthly', 'quarterly', 'semester', 'yearly'],
            'quick_presets': ['current_month', 'current_quarter', 'current_semester', 'current_year'],
            'layout': {'viewer_variant': 'executive_dashboard'},
        },
    }

    def __init__(self, report_definition_repository=None, report_version_repository=None, dataset_repository=None, dataset_version_repository=None):
        """Inisialisasi dependency service report dan dataset."""

        super().__init__(repository=report_definition_repository or AnalyticsReportDefinitionRepository())
        self.version_repository = report_version_repository or AnalyticsReportVersionRepository()
        self.dataset_repository = dataset_repository or AnalyticsDatasetRepository()
        self.dataset_version_repository = dataset_version_repository or AnalyticsDatasetVersionRepository()

    def create_report_bundle(self, data, actor=None):
        """Membuat report definition sekaligus draft version awal berbasis dataset."""

        report_data = data.get('report') if isinstance(data.get('report'), dict) else data
        draft_data = data.get('draft_version') if isinstance(data.get('draft_version'), dict) else {}

        report = self.create_report_definition(report_data, actor=actor)
        draft_version = self.create_report_version(report.id, draft_data, actor=actor)
        return {
            'report': report,
            'draft_version': draft_version,
        }

    def update_report_bundle(self, report_definition_id, data, actor=None):
        """Memperbarui report definition dan draft version aktif secara atomik."""

        report_data = data.get('report') if isinstance(data.get('report'), dict) else data
        draft_data = data.get('draft_version') if isinstance(data.get('draft_version'), dict) else {}

        report = self.update_report_definition(report_definition_id, report_data, actor=actor)
        draft_version = self.upsert_draft_version(report.id, draft_data, actor=actor)
        return {
            'report': report,
            'draft_version': draft_version,
        }

    def create_report_definition(self, data, actor=None):
        """Membuat definisi report analytics baru."""

        normalized = self._normalize_report_definition_payload(data)
        report = AnalyticsReportDefinition(
            uuid=str(uuid.uuid4()),
            report_key=normalized['report_key'],
            dataset_id=normalized['dataset_id'],
            name=normalized['name'],
            description=normalized['description'],
            report_type=normalized['report_type'],
            category_key=normalized['category_key'],
            status=normalized['status'],
            is_active=normalized['is_active'],
            settings_json=normalized['settings_json'],
            tags_json=normalized['tags_json'],
        )
        self._apply_actor_audit(report, actor, action='create')
        return self.repository.save(report)

    def update_report_definition(self, report_definition_id, data, actor=None):
        """Memperbarui definisi report analytics yang sudah ada."""

        report = self.repository.get_by_id(report_definition_id)
        if not report:
            raise ValueError('Analytics report definition tidak ditemukan.')

        normalized = self._normalize_report_definition_payload(data, existing=report)
        report.report_key = normalized['report_key']
        report.dataset_id = normalized['dataset_id']
        report.name = normalized['name']
        report.description = normalized['description']
        report.report_type = normalized['report_type']
        report.category_key = normalized['category_key']
        report.status = normalized['status']
        report.is_active = normalized['is_active']
        report.settings_json = normalized['settings_json']
        report.tags_json = normalized['tags_json']
        self._apply_actor_audit(report, actor, action='update')
        return self.repository.save(report)

    def create_report_version(self, report_definition_id, data, actor=None):
        """Membuat version report analytics baru."""

        report = self.repository.get_by_id(report_definition_id)
        if not report:
            raise ValueError('Analytics report definition tidak ditemukan.')

        normalized = self._normalize_report_version_payload(report, data)
        version = AnalyticsReportVersion(
            uuid=str(uuid.uuid4()),
            report_definition_id=report_definition_id,
            version_number=self.version_repository.get_next_version_number(report_definition_id),
            dataset_version_id=normalized['dataset_version_id'],
            status=normalized['status'],
            is_current_draft=normalized['is_current_draft'],
            is_current_published=normalized['is_current_published'],
            title=normalized['title'],
            meta_description=normalized['meta_description'],
            structure_json=normalized['structure_json'],
            narrative_guidance_json=normalized['narrative_guidance_json'],
            published_at=normalized['published_at'],
        )
        self._apply_actor_audit(version, actor, action='create')
        return self.version_repository.save(version)

    def upsert_draft_version(self, report_definition_id, data, actor=None):
        """Meng-update draft aktif atau membuat draft baru bila belum ada."""

        report = self.repository.get_by_id(report_definition_id)
        if not report:
            raise ValueError('Analytics report definition tidak ditemukan.')

        draft_version = self.version_repository.get_draft_version(report_definition_id)
        if not draft_version:
            return self.create_report_version(report_definition_id, data, actor=actor)

        normalized = self._normalize_report_version_payload(report, data, existing=draft_version)
        draft_version.dataset_version_id = normalized['dataset_version_id']
        draft_version.status = normalized['status']
        draft_version.is_current_draft = normalized['is_current_draft']
        draft_version.is_current_published = normalized['is_current_published']
        draft_version.title = normalized['title']
        draft_version.meta_description = normalized['meta_description']
        draft_version.structure_json = normalized['structure_json']
        draft_version.narrative_guidance_json = normalized['narrative_guidance_json']
        self._apply_actor_audit(draft_version, actor, action='update')
        return self.version_repository.save(draft_version)

    def publish_report_version(self, version_id, actor=None):
        """Mempublish report version dan menandai definisi report sebagai active."""

        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ValueError('Analytics report version tidak ditemukan.')
        if not getattr(version, 'dataset_version_id', None):
            raise ValueError('Report version wajib terhubung ke dataset version sebelum dipublish.')

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
                if not getattr(report_definition, 'dataset_id', None) and getattr(version.definition, 'dataset_id', None):
                    report_definition.dataset_id = version.definition.dataset_id
                self._apply_actor_audit(report_definition, actor, action='update')
                self.repository.save(report_definition)

            return saved_version
        except Exception:
            db.session.rollback()
            raise

    def _normalize_report_definition_payload(self, data, existing=None):
        data = data or {}
        settings_json = self._coerce_dict(data.get('settings_json'), getattr(existing, 'settings_json', None) or {})
        tags_json = self._coerce_list(data.get('tags_json', getattr(existing, 'tags_json', None) or []))
        report_family = data.get('report_family', settings_json.get('report_family') or 'custom')
        dataset_id = data.get('dataset_id', getattr(existing, 'dataset_id', None))
        if dataset_id in ('', None):
            dataset_id = None
        if dataset_id is not None:
            dataset_id = int(dataset_id)
            dataset = self.dataset_repository.get_by_id(dataset_id)
            if not dataset:
                raise ValueError('Dataset analytics untuk report tidak ditemukan.')
            settings_json = {
                **settings_json,
                'linked_dataset_key': getattr(dataset, 'dataset_key', None),
                'linked_dataset_name': getattr(dataset, 'name', None),
            }

        report_key = data.get('report_key', getattr(existing, 'report_key', None))
        if not report_key:
            raise ValueError('report_key wajib diisi.')

        report_type = data.get('report_type', getattr(existing, 'report_type', None) or AnalyticsReportDefinition.TYPE_CUSTOM)
        report_type = self.REPORT_TYPE_ALIASES.get(report_type, report_type)
        if report_type not in self.ALLOWED_REPORT_TYPES:
            raise ValueError('report_type analytics report tidak valid.')

        settings_json = {
            **settings_json,
            'report_family': report_family,
            'report_template_key': data.get('report_template_key', settings_json.get('report_template_key') or report_family),
        }

        return {
            'report_key': report_key,
            'dataset_id': dataset_id,
            'name': data.get('name') or getattr(existing, 'name', None) or report_key,
            'description': data.get('description', getattr(existing, 'description', None)),
            'report_type': report_type,
            'category_key': data.get('category_key', getattr(existing, 'category_key', None)),
            'status': data.get('status', getattr(existing, 'status', None) or AnalyticsReportDefinition.STATUS_DRAFT),
            'is_active': data.get('is_active', getattr(existing, 'is_active', None) if existing is not None else True),
            'settings_json': settings_json,
            'tags_json': tags_json,
        }

    def _normalize_report_version_payload(self, report, data, existing=None):
        data = data or {}
        dataset_version_id = data.get('dataset_version_id', getattr(existing, 'dataset_version_id', None))
        if dataset_version_id in ('', None):
            dataset_version_id = None
        if dataset_version_id is None and getattr(report, 'dataset_id', None):
            published_version = self.dataset_version_repository.get_published_version(report.dataset_id)
            draft_version = self.dataset_version_repository.get_draft_version(report.dataset_id)
            preferred_version = draft_version or published_version
            dataset_version_id = getattr(preferred_version, 'id', None)
        if dataset_version_id is not None:
            dataset_version_id = int(dataset_version_id)
            dataset_version = self.dataset_version_repository.get_by_id(dataset_version_id)
            if not dataset_version:
                raise ValueError('Dataset version untuk report tidak ditemukan.')
        else:
            dataset_version = None

        structure_json = self._coerce_dict(data.get('structure_json'), getattr(existing, 'structure_json', None) or {})
        structure_json = self._normalize_report_structure(report, dataset_version, structure_json, data)
        narrative_guidance_json = self._coerce_dict(data.get('narrative_guidance_json'), getattr(existing, 'narrative_guidance_json', None) or {})
        narrative_guidance_json = {
            **narrative_guidance_json,
            'intro': data.get('narrative_intro', narrative_guidance_json.get('intro')),
            'methodology': data.get('narrative_methodology', narrative_guidance_json.get('methodology')),
            'summary_prompt': data.get('summary_prompt', narrative_guidance_json.get('summary_prompt')),
        }

        return {
            'dataset_version_id': dataset_version_id,
            'status': data.get('status', getattr(existing, 'status', None) or AnalyticsReportVersion.STATUS_DRAFT),
            'is_current_draft': data.get('is_current_draft', getattr(existing, 'is_current_draft', None) if existing is not None else True),
            'is_current_published': data.get('is_current_published', getattr(existing, 'is_current_published', None) if existing is not None else False),
            'title': data.get('title') or getattr(existing, 'title', None) or getattr(report, 'name', None) or 'Untitled report version',
            'meta_description': data.get('meta_description', getattr(existing, 'meta_description', None)),
            'structure_json': structure_json,
            'narrative_guidance_json': narrative_guidance_json,
            'published_at': data.get('published_at', getattr(existing, 'published_at', None)),
        }

    def _normalize_report_structure(self, report, dataset_version, structure_json, data):
        report_settings = getattr(report, 'settings_json', None) or {}
        report_family = data.get('report_family') or report_settings.get('report_family') or 'custom'
        family_defaults = self.REPORT_FAMILY_DEFAULTS.get(report_family, self.REPORT_FAMILY_DEFAULTS['custom'])
        blocks = self._coerce_list(data.get('blocks') or structure_json.get('blocks') or structure_json.get('block_definitions'))
        if not blocks:
            dataset = getattr(report, 'dataset', None)
            dataset_settings = getattr(dataset, 'settings_json', None) or {}
            suggested_blocks = self._coerce_list(dataset_settings.get('suggested_report_blocks'))
            blocks = [
                {
                    'type': item,
                    'title': str(item).replace('_', ' ').title(),
                    'order': index,
                    'config': {},
                }
                for index, item in enumerate((suggested_blocks or family_defaults.get('blocks') or self.DEFAULT_REPORT_BLOCKS), start=1)
            ]
        else:
            normalized_blocks = []
            for index, block in enumerate(blocks, start=1):
                if isinstance(block, str):
                    normalized_blocks.append({'type': block, 'title': block.replace('_', ' ').title(), 'order': index, 'config': {}})
                elif isinstance(block, dict):
                    normalized_blocks.append({
                        'type': block.get('type') or block.get('block_type') or f'block_{index}',
                        'title': block.get('title') or block.get('label') or f'Block {index}',
                        'order': block.get('order', index),
                        'config': self._coerce_dict(block.get('config'), {}),
                    })
            blocks = normalized_blocks
        if not blocks:
            raise ValueError('Report builder wajib memiliki minimal satu block.')

        period_config = self._coerce_dict(data.get('period_preset_config'), structure_json.get('period_preset_config') or {})
        supported_period_modes = self._coerce_list(data.get('supported_period_modes') or period_config.get('supported_period_modes'))
        quick_presets = self._coerce_list(data.get('quick_presets') or period_config.get('quick_presets'))
        if not supported_period_modes:
            dataset = getattr(report, 'dataset', None)
            dataset_settings = getattr(dataset, 'settings_json', None) or {}
            supported_period_modes = self._coerce_list(dataset_settings.get('supported_period_modes')) or family_defaults.get('supported_period_modes') or ['quarterly', 'semester', 'yearly']
        if not quick_presets:
            quick_presets = family_defaults.get('quick_presets') or self.DEFAULT_PERIOD_PRESETS

        filter_schema = self._coerce_dict(data.get('filter_schema'), structure_json.get('filter_schema') or {})
        layout = self._coerce_dict(data.get('layout'), structure_json.get('layout') or {})
        layout = {
            **self._coerce_dict(family_defaults.get('layout'), {}),
            **layout,
            'report_family': report_family,
            'block_order_strategy': 'explicit_order',
        }
        dataset_contract = self._coerce_dict(structure_json.get('dataset_contract'), {})
        curated_fields = self._coerce_list(dataset_contract.get('curated_fields'))
        if dataset_version:
            curated_fields = self._build_curated_dataset_fields(dataset_version)
            dataset_contract = {
                **dataset_contract,
                'dataset_id': getattr(report, 'dataset_id', None),
                'dataset_version_id': dataset_version.id,
                'dataset_version_number': dataset_version.version_number,
                'grain_key': getattr(dataset_version, 'grain_key', None),
                'output_schema_json': getattr(dataset_version, 'output_schema_json', None) or [],
                'dimension_definitions_json': getattr(dataset_version, 'dimension_definitions_json', None) or [],
                'metric_definitions_json': getattr(dataset_version, 'metric_definitions_json', None) or [],
                'curated_fields': curated_fields,
                'run_binding': self._build_report_run_binding(report, dataset_version),
            }
        normalized_blocks = [self._normalize_report_block_config(block, curated_fields) for block in blocks]

        return {
            **structure_json,
            'dataset_contract': dataset_contract,
            'period_preset_config': {
                **period_config,
                'supported_period_modes': supported_period_modes,
                'quick_presets': quick_presets,
                'default_mode': data.get('default_period_mode', period_config.get('default_mode') or supported_period_modes[0]),
            },
            'filter_schema': filter_schema,
            'layout': layout,
            'blocks': normalized_blocks,
        }

    def _build_curated_dataset_fields(self, dataset_version):
        curated_fields = []
        seen_keys = set()
        metric_keys = self._extract_field_keys(getattr(dataset_version, 'metric_definitions_json', None) or [])
        dimension_keys = self._extract_field_keys(getattr(dataset_version, 'dimension_definitions_json', None) or [])
        field_groups = [
            ('output_schema', getattr(dataset_version, 'output_schema_json', None) or []),
            ('dimension', getattr(dataset_version, 'dimension_definitions_json', None) or []),
            ('metric', getattr(dataset_version, 'metric_definitions_json', None) or []),
        ]
        for source_name, field_defs in field_groups:
            for field in self._coerce_list(field_defs):
                field_payload = field if isinstance(field, dict) else {'key': field}
                key = field_payload.get('key') or field_payload.get('field_key') or field_payload.get('name')
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                field_type = field_payload.get('type') or field_payload.get('data_type') or 'string'
                role_source_name = self._resolve_curated_role_source(key, source_name, metric_keys, dimension_keys)
                curated_fields.append(
                    {
                        'key': key,
                        'label': field_payload.get('label') or field_payload.get('title') or key.replace('_', ' ').title(),
                        'type': field_type,
                        'source': source_name,
                        'role': self._infer_curated_field_role(key, field_type, role_source_name),
                    }
                )
        return curated_fields

    def _extract_field_keys(self, field_defs):
        keys = set()
        for field in self._coerce_list(field_defs):
            field_payload = field if isinstance(field, dict) else {'key': field}
            key = field_payload.get('key') or field_payload.get('field_key') or field_payload.get('name')
            if key:
                keys.add(key)
        return keys

    def _resolve_curated_role_source(self, key, source_name, metric_keys, dimension_keys):
        if key in metric_keys:
            return 'metric'
        if key in dimension_keys:
            return 'dimension'
        return source_name

    def _infer_curated_field_role(self, key, field_type, source_name):
        normalized_key = str(key or '').strip().lower()
        normalized_type = str(field_type or '').strip().lower()
        if normalized_key in {'tanggal', 'date', 'submitted_at', 'period_date'} or normalized_type in {'date', 'datetime'}:
            return 'date'
        if normalized_key in {'latitude', 'lat'} or 'latitude' in normalized_key:
            return 'geo_latitude'
        if normalized_key in {'longitude', 'lng', 'lon'} or 'longitude' in normalized_key:
            return 'geo_longitude'
        if source_name == 'metric':
            return 'metric'
        if source_name == 'dimension':
            return 'dimension'
        if normalized_type in {'integer', 'number', 'numeric', 'float', 'decimal'} and any(token in normalized_key for token in ['total', 'jumlah', 'count', 'pct', 'percent', 'achievement', 'score', 'target', 'realisasi', 'capaian', 'deviasi', 'progres', 'progress', 'nilai']):
            return 'metric'
        return 'dimension'

    def _build_report_run_binding(self, report, dataset_version):
        dataset = getattr(report, 'dataset', None)
        if dataset is None and getattr(report, 'dataset_id', None):
            dataset = self.dataset_repository.get_by_id(report.dataset_id)
        return {
            'dataset_id': getattr(report, 'dataset_id', None),
            'dataset_key': getattr(dataset, 'dataset_key', None),
            'dataset_version_id': getattr(dataset_version, 'id', None),
            'dataset_version_number': getattr(dataset_version, 'version_number', None),
            'report_title': getattr(report, 'name', None),
            'report_category_key': getattr(report, 'category_key', None),
            'selection_mode': 'latest_succeeded_run',
        }

    def _normalize_report_block_config(self, block, curated_fields):
        block_type = block.get('type')
        config = self._coerce_dict(block.get('config'), {})
        metric_field_keys = [field['key'] for field in curated_fields if field.get('role') == 'metric']
        dimension_field_keys = [field['key'] for field in curated_fields if field.get('role') == 'dimension']
        date_field_keys = [field['key'] for field in curated_fields if field.get('role') == 'date']
        latitude_field = next((field['key'] for field in curated_fields if field.get('role') == 'geo_latitude'), None)
        longitude_field = next((field['key'] for field in curated_fields if field.get('role') == 'geo_longitude'), None)

        normalized_config = {**config}
        if block_type == 'metric_cards':
            normalized_config['metric_keys'] = self._pick_allowed_field_keys(
                config.get('metric_keys') or config.get('selected_field_keys'),
                metric_field_keys,
                fallback=metric_field_keys[:4],
            )
        elif block_type == 'plotly_timeseries':
            x_key = config.get('x_key') or next(iter(date_field_keys or dimension_field_keys or metric_field_keys), None)
            normalized_series = []
            for series in self._coerce_list(config.get('series')):
                if not isinstance(series, dict):
                    continue
                key = series.get('key')
                if key and key in metric_field_keys:
                    normalized_series.append(
                        {
                            'key': key,
                            'label': series.get('label') or key.replace('_', ' ').title(),
                            'aggregation': series.get('aggregation') or 'sum',
                        }
                    )
            if not normalized_series:
                normalized_series = [
                    {
                        'key': key,
                        'label': key.replace('_', ' ').title(),
                        'aggregation': 'sum',
                    }
                    for key in metric_field_keys[:3]
                ]
            normalized_config['x_key'] = x_key
            normalized_config['series'] = normalized_series
        elif block_type == 'detail_table':
            fallback_columns = (
                date_field_keys[:1]
                + dimension_field_keys[:1]
                + metric_field_keys[:2]
                + dimension_field_keys[1:3]
            )[:5]
            normalized_config['column_keys'] = self._pick_allowed_field_keys(
                config.get('column_keys') or config.get('selected_field_keys'),
                [field['key'] for field in curated_fields],
                fallback=fallback_columns,
            )
        elif block_type == 'geo_map':
            label_field = config.get('label_field') or next(iter(dimension_field_keys or metric_field_keys), None)
            normalized_config['latitude_field'] = config.get('latitude_field') if config.get('latitude_field') in [field['key'] for field in curated_fields] else latitude_field
            normalized_config['longitude_field'] = config.get('longitude_field') if config.get('longitude_field') in [field['key'] for field in curated_fields] else longitude_field
            normalized_config['label_field'] = label_field
        elif block_type == 'narrative':
            normalized_config['focus_field_keys'] = self._pick_allowed_field_keys(
                config.get('focus_field_keys') or config.get('selected_field_keys'),
                [field['key'] for field in curated_fields],
                fallback=metric_field_keys[:2],
            )
            normalized_config['source_mode'] = config.get('source_mode') or 'auto_summary'

        return {
            **block,
            'config': normalized_config,
        }

    def _pick_allowed_field_keys(self, requested_keys, allowed_keys, fallback=None):
        allowed_set = set(self._coerce_list(allowed_keys))
        selected = [key for key in self._coerce_list(requested_keys) if key in allowed_set]
        if selected:
            return selected
        return [key for key in self._coerce_list(fallback) if key in allowed_set]

    def _coerce_dict(self, value, default=None):
        if isinstance(value, dict):
            return value
        return default or {}

    def _coerce_list(self, value):
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

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
