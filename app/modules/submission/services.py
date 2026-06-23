"""Service layer domain submission.

Modul ini mengorkestrasi lifecycle submission form, mulai dari draft, submit final, validasi payload dasar, resolusi periode pelaporan, pencatatan event audit, hingga perhitungan freshness data berbasis submissions."""

import uuid

from app.core.access import (
    build_actor_context,
    can_submit_form,
    can_update_submission,
    can_view_submission,
    derive_submission_policy_key,
    enrich_scope,
)
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
    """Service utama untuk draft, submit final, dan audit event submission.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = SubmissionService()
    """

    def __init__(
        self,
        submission_repository=None,
        event_repository=None,
        form_repository=None,
        version_repository=None,
        period_repository=None,
    ):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            submission_repository (Any): Parameter `submission_repository` untuk operasi init.
            event_repository (Any): Parameter `event_repository` untuk operasi init.
            form_repository (Any): Parameter `form_repository` untuk operasi init.
            version_repository (Any): Parameter `version_repository` untuk operasi init.
            period_repository (Any): Parameter `period_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = SubmissionService()
        """

        super().__init__(repository=submission_repository or SubmissionRepository())
        self.event_repository = event_repository or SubmissionEventRepository()
        self.form_repository = form_repository or FormRepository()
        self.version_repository = version_repository or FormVersionRepository()
        self.period_repository = period_repository or ReportingPeriodRepository()

    def create_draft(self, form_id, payload, actor=None, context=None):
        """Membuat submission draft tanpa status submit final.

        Args:
            form_id (Any): Primary key internal form target.
            payload (Any): Payload bisnis yang akan divalidasi atau dipersist.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            context (Any): Konteks tambahan runtime seperti source, scope, meta, atau subject.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_draft(form_id=..., payload=..., actor=...)
        """

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
        """Membuat submission final yang sudah tervalidasi dan tercatat event auditnya.

        Args:
            form_id (Any): Primary key internal form target.
            payload (Any): Payload bisnis yang akan divalidasi atau dipersist.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            context (Any): Konteks tambahan runtime seperti source, scope, meta, atau subject.
            reporting_year (Any): Parameter `reporting_year` untuk operasi submit.
            reporting_period_id (Any): Parameter `reporting_period_id` untuk operasi submit.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service.submit(form_id=..., payload=..., actor=...)
        """

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
        """Memvalidasi payload submission dan mengembalikan snapshot hasil validasi.

        Args:
            payload (Any): Payload bisnis yang akan divalidasi atau dipersist.
            form_version (Any): Entity version form yang menjadi acuan proses.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.validate_payload(payload=..., form_version=...)
        """

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
        """Menentukan konteks reporting year dan reporting period yang dipakai submission.

        Args:
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            reporting_year (Any): Parameter `reporting_year` untuk operasi resolve reporting period.
            reporting_period_id (Any): Parameter `reporting_period_id` untuk operasi resolve reporting period.
            context (Any): Konteks tambahan runtime seperti source, scope, meta, atau subject.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.resolve_reporting_period(actor=..., reporting_year=..., reporting_period_id=...)
        """

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
        """Mencatat event audit submission seperti created, submitted, atau validation_failed.

        Args:
            submission (Any): Parameter `submission` untuk operasi add event.
            event_type (Any): Parameter `event_type` untuk operasi add event.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            context (Any): Konteks tambahan runtime seperti source, scope, meta, atau subject.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.add_event(submission=..., event_type=..., actor=...)
        """

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
        """Menghitung freshness data analytics berdasarkan submitted_at submission resmi.

        Args:
            form_id (Any): Primary key internal form target.
            reporting_year (Any): Parameter `reporting_year` untuk operasi get data freshness.
            reporting_period_id (Any): Parameter `reporting_period_id` untuk operasi get data freshness.
            statuses (Any): Daftar status submission yang ikut difilter.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_data_freshness(form_id=..., reporting_year=..., reporting_period_id=...)
        """

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

    def list_submissions(self, actor=None, form_id=None, reporting_year=None, reporting_period_id=None, statuses=None):
        """Mengambil submission yang boleh dilihat actor untuk UI tabel submission."""
        submissions = self.repository.list_filtered(
            form_id=form_id,
            reporting_year=reporting_year,
            reporting_period_id=reporting_period_id,
            statuses=statuses,
        )
        if actor is None:
            return submissions
        return [submission for submission in submissions if can_view_submission(actor, submission)]

    def get_submission(self, submission_id, actor=None):
        """Mengambil satu submission dengan guard ABAC detail."""
        submission = self.repository.get_by_id(submission_id)
        if not submission or getattr(submission, 'deleted_at', None) is not None:
            raise ValueError('Submission tidak ditemukan.')
        if actor is not None and not can_view_submission(actor, submission):
            raise PermissionError('Actor tidak memiliki izin melihat submission ini.')
        return submission

    def update_submission(self, submission_id, payload, actor=None, refresh_submitted_at=True):
        """Mengubah payload submission resmi dan menggeser submitted_at untuk freshness."""
        submission = self.get_submission(submission_id, actor=actor)
        if actor is not None and not can_update_submission(actor, submission):
            raise PermissionError('Actor tidak memiliki izin mengubah submission ini.')
        if payload is None or not isinstance(payload, dict):
            raise ValueError('Payload submission wajib berupa object/dict.')

        form_version = getattr(submission, 'form_version', None) or self.version_repository.get_by_id(submission.form_version_id)
        validation_snapshot = self.validate_payload(payload, form_version)

        try:
            submission.payload = payload
            submission.validation_snapshot = validation_snapshot
            if refresh_submitted_at and submission.status == 'submitted':
                submission.submitted_at = now_utc()
            self._apply_actor_audit(submission, actor, action='update')
            submission = self.repository.save(submission)
            self.add_event(
                submission,
                'updated',
                actor=actor,
                context={
                    'refresh_submitted_at': bool(refresh_submitted_at),
                    'freshness_source': 'submissions.submitted_at',
                    'validation_snapshot': validation_snapshot,
                },
            )
            return submission
        except Exception:
            db.session.rollback()
            raise

    def resolve_submission_scope(self, form=None, actor=None, context=None):
        """Menentukan scope owner submission dari context, actor, atau konfigurasi form.

        Args:
            form (Any): Entity form yang sudah di-resolve sebelumnya.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            context (Any): Konteks tambahan runtime seperti source, scope, meta, atau subject.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.resolve_submission_scope(form=..., actor=..., context=...)
        """

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
        """Menyusun subject resource yang direferensikan submission dari context runtime.

        Args:
            context (Any): Konteks tambahan runtime seperti source, scope, meta, atau subject.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.resolve_submission_subject(context=...)
        """

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
        """Helper internal untuk generate submission number.

        Args:
            reporting_year (Any): Parameter `reporting_year` untuk operasi generate submission number.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._generate_submission_number(reporting_year=...)
        """

        return f"SUB-{reporting_year}-{uuid.uuid4().hex[:12].upper()}"

    def _get_actor_active_year(self, actor):
        """Helper internal untuk get actor active year.

        Args:
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._get_actor_active_year(actor=...)
        """

        return build_actor_context(actor).get('active_year')

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
