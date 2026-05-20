import uuid

from app.core.access import build_actor_context, can_submit_form, derive_submission_policy_key, enrich_scope
from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc

from app.modules.form.repositories import FormRepository, FormVersionRepository

from .models import Submission, SubmissionEvent
from .repositories import (
    ReportingPeriodRepository,
    SubmissionEventRepository,
    SubmissionRepository,
)


class SubmissionService(BaseService):
    def __init__(
        self,
        submission_repository=None,
        event_repository=None,
        form_repository=None,
        version_repository=None,
        period_repository=None,
    ):
        super().__init__(repository=submission_repository or SubmissionRepository())
        self.event_repository = event_repository or SubmissionEventRepository()
        self.form_repository = form_repository or FormRepository()
        self.version_repository = version_repository or FormVersionRepository()
        self.period_repository = period_repository or ReportingPeriodRepository()

    def create_draft(self, form_id, payload, actor=None, context=None):
        form = self.form_repository.get_by_id(form_id)
        if not form:
            raise ValueError('Form tidak ditemukan.')
        if not can_submit_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengirim submission untuk form ini.')

        form_version = self.version_repository.get_published_version(form_id)
        if not form_version:
            raise ValueError('Form belum memiliki published version.')

        reporting_context = self.resolve_reporting_period(actor=actor, context=context)
        scope_context = self.resolve_submission_scope(form=form, actor=actor, context=context)
        subject_context = self.resolve_submission_subject(context=context)

        submission = Submission(
            uuid=str(uuid.uuid4()),
            submission_number=self._generate_submission_number(reporting_context['reporting_year']),
            form_id=form.id,
            form_version_id=form_version.id,
            reporting_year=reporting_context['reporting_year'],
            reporting_period_id=reporting_context.get('reporting_period_id'),
            status='draft',
            payload=payload or {},
            meta=(context or {}).get('meta') if context else None,
            owner_scope_type=scope_context.get('type') or 'global',
            owner_scope_code=scope_context.get('code'),
            owner_scope_name=scope_context.get('name'),
            owner_scope_path=scope_context.get('path'),
            subject_type=subject_context.get('type'),
            subject_ref_id=subject_context.get('ref_id'),
            subject_ref_uuid=subject_context.get('ref_uuid'),
            subject_ref_code=subject_context.get('ref_code'),
            subject_ref_name=subject_context.get('ref_name'),
            access_policy_key=derive_submission_policy_key(form=form, context=context),
            source_type=(context or {}).get('source_type') if context else None,
            source_ref=(context or {}).get('source_ref') if context else None,
        )
        self._apply_actor_audit(submission, actor, action='create')

        try:
            submission = self.repository.save(submission)
            self.add_event(submission, 'created', actor=actor, context=context)
            return submission
        except Exception:
            db.session.rollback()
            raise

    def submit(
        self,
        form_id,
        payload,
        actor=None,
        context=None,
        reporting_year=None,
        reporting_period_id=None,
    ):
        form = self.form_repository.get_by_id(form_id)
        if not form:
            raise ValueError('Form tidak ditemukan.')
        if not can_submit_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengirim submission untuk form ini.')

        form_version = self.version_repository.get_published_version(form_id)
        if not form_version:
            raise ValueError('Form belum memiliki published version.')

        try:
            validation_snapshot = self.validate_payload(payload, form_version)
        except ValueError as error:
            self.add_event(
                None,
                'validation_failed',
                actor=actor,
                context={
                    'error': str(error),
                    'form_id': form.id,
                    'form_version_id': form_version.id,
                },
            )
            raise

        reporting_context = self.resolve_reporting_period(
            actor=actor,
            reporting_year=reporting_year,
            reporting_period_id=reporting_period_id,
            context=context,
        )
        scope_context = self.resolve_submission_scope(form=form, actor=actor, context=context)
        subject_context = self.resolve_submission_subject(context=context)

        submission = Submission(
            uuid=str(uuid.uuid4()),
            submission_number=self._generate_submission_number(reporting_context['reporting_year']),
            form_id=form.id,
            form_version_id=form_version.id,
            reporting_year=reporting_context['reporting_year'],
            reporting_period_id=reporting_context.get('reporting_period_id'),
            status='submitted',
            submitted_at=now_utc(),
            payload=payload or {},
            meta=(context or {}).get('meta') if context else None,
            validation_snapshot=validation_snapshot,
            submitted_by=getattr(actor, 'id', None) if actor else None,
            submitted_by_uuid=getattr(actor, 'uuid', None) if actor else None,
            owner_scope_type=scope_context.get('type') or 'global',
            owner_scope_code=scope_context.get('code'),
            owner_scope_name=scope_context.get('name'),
            owner_scope_path=scope_context.get('path'),
            subject_type=subject_context.get('type'),
            subject_ref_id=subject_context.get('ref_id'),
            subject_ref_uuid=subject_context.get('ref_uuid'),
            subject_ref_code=subject_context.get('ref_code'),
            subject_ref_name=subject_context.get('ref_name'),
            access_policy_key=derive_submission_policy_key(form=form, context=context),
            source_type=(context or {}).get('source_type') if context else None,
            source_ref=(context or {}).get('source_ref') if context else None,
        )
        self._apply_actor_audit(submission, actor, action='create')

        try:
            submission = self.repository.save(submission)
            self.add_event(submission, 'validation_passed', actor=actor, context=validation_snapshot)
            self.add_event(submission, 'submitted', actor=actor, context=context)
            return submission
        except Exception:
            db.session.rollback()
            raise

    def validate_payload(self, payload, form_version):
        if payload is None:
            raise ValueError('Payload submission wajib diisi.')
        if not isinstance(payload, dict):
            raise ValueError('Payload submission wajib berupa object/dict.')

        return {
            'is_valid': True,
            'schema_version_id': getattr(form_version, 'id', None),
            'validated_at': now_utc().isoformat(),
        }

    def resolve_reporting_period(
        self,
        actor=None,
        reporting_year=None,
        reporting_period_id=None,
        context=None,
    ):
        if reporting_period_id is not None:
            period = self.period_repository.get_by_id(reporting_period_id)
            if not period:
                raise ValueError('Reporting period tidak ditemukan.')
            return {
                'reporting_period_id': period.id,
                'reporting_year': period.year,
            }

        resolved_year = reporting_year
        if resolved_year is None:
            resolved_year = self._get_actor_active_year(actor)
        if resolved_year is None and context:
            resolved_year = context.get('reporting_year')
        if resolved_year is None:
            resolved_year = now_utc().year

        active_period = self.period_repository.get_active_by_year(resolved_year)

        return {
            'reporting_period_id': getattr(active_period, 'id', None) if active_period else None,
            'reporting_year': resolved_year,
        }

    def add_event(self, submission, event_type, actor=None, context=None):
        event = SubmissionEvent(
            uuid=str(uuid.uuid4()),
            submission_id=getattr(submission, 'id', None),
            event_type=event_type,
            event_at=now_utc(),
            actor_user_id=getattr(actor, 'id', None) if actor else None,
            actor_user_uuid=getattr(actor, 'uuid', None) if actor else None,
            context=context,
        )
        self._apply_actor_audit(event, actor, action='create')
        return self.event_repository.save(event)

    def get_data_freshness(
        self,
        form_id=None,
        reporting_year=None,
        reporting_period_id=None,
        statuses=None,
    ):
        data_last_updated_at = self.repository.get_last_submitted_at(
            form_id=form_id,
            reporting_year=reporting_year,
            reporting_period_id=reporting_period_id,
            statuses=statuses,
        )

        return {
            'data_last_updated_at': data_last_updated_at,
            'source': 'submissions.submitted_at',
            'form_id': form_id,
            'reporting_year': reporting_year,
            'reporting_period_id': reporting_period_id,
        }

    def resolve_submission_scope(self, form=None, actor=None, context=None):
        context = context or {}
        explicit_scope = context.get('owner_scope') or context.get('scope')
        if isinstance(explicit_scope, dict):
            enriched_scope = enrich_scope(explicit_scope)
            if enriched_scope:
                return enriched_scope

        actor_scope = build_actor_context(actor).get('scope') if actor else None
        if actor_scope:
            return actor_scope

        return enrich_scope(
            {
                'type': getattr(form, 'target_scope_type', None) or getattr(form, 'owner_scope_type', None) or 'global',
                'code': getattr(form, 'target_scope_code', None) or getattr(form, 'owner_scope_code', None),
                'name': getattr(form, 'target_scope_name', None) or getattr(form, 'owner_scope_name', None),
                'path': getattr(form, 'target_scope_path', None) or getattr(form, 'owner_scope_path', None),
            }
        ) or {'type': 'global'}

    def resolve_submission_subject(self, context=None):
        context = context or {}
        subject = context.get('subject')
        if isinstance(subject, dict):
            return subject

        return {
            'type': context.get('subject_type'),
            'ref_id': context.get('subject_ref_id'),
            'ref_uuid': context.get('subject_ref_uuid'),
            'ref_code': context.get('subject_ref_code'),
            'ref_name': context.get('subject_ref_name'),
        }

    def _generate_submission_number(self, reporting_year):
        return f"SUB-{reporting_year}-{uuid.uuid4().hex[:12].upper()}"

    def _get_actor_active_year(self, actor):
        return build_actor_context(actor).get('active_year')

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
