"""Service layer domain form.

Modul ini menampung orkestrasi business rule untuk registri form dan versioning schema Form.io, termasuk pembuatan form, draft version, publish, archive, serta snapshot scope/access policy yang dibutuhkan domain enterprise."""

import uuid

from app.core.access import can_archive_form, can_create_form, can_publish_form, can_update_form
from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc

from .models import Form, FormVersion
from .repositories import FormRepository, FormVersionRepository


class FormService(BaseService):
    """Service orkestrasi identitas dan lifecycle form utama.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = FormService()
    """

    def __init__(self, form_repository=None, version_service=None):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            form_repository (Any): Parameter `form_repository` untuk operasi init.
            version_service (Any): Parameter `version_service` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = FormService()
        """

        super().__init__(repository=form_repository or FormRepository())
        self.version_service = version_service or FormVersionService()

    def create_form(self, data, actor=None):
        """Membuat form baru beserta draft version awal bila schema awal ikut dikirim.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_form(data=..., actor=...)
        """

        if not can_create_form(actor):
            raise PermissionError('Actor tidak memiliki izin membuat form.')

        code = data.get('code')
        slug = data.get('slug')
        name = data.get('name')

        if not code:
            raise ValueError('Kode form wajib diisi.')
        if not slug:
            raise ValueError('Slug form wajib diisi.')
        if not name:
            raise ValueError('Nama form wajib diisi.')
        if self.repository.exists_code(code):
            raise ValueError('Kode form sudah digunakan.')
        if self.repository.exists_slug(slug):
            raise ValueError('Slug form sudah digunakan.')

        form = Form(
            uuid=str(uuid.uuid4()),
            code=code,
            slug=slug,
            name=name,
            description=data.get('description'),
            status=data.get('status', 'draft'),
            visibility=data.get('visibility', 'internal'),
            settings=data.get('settings'),
            owner_user_id=data.get('owner_user_id'),
            owner_scope_type=self._resolve_scope_value(data, 'owner_scope', 'type', default='global'),
            owner_scope_code=self._resolve_scope_value(data, 'owner_scope', 'code'),
            owner_scope_name=self._resolve_scope_value(data, 'owner_scope', 'name'),
            owner_scope_path=self._resolve_scope_value(data, 'owner_scope', 'path'),
            target_scope_type=self._resolve_scope_value(
                data,
                'target_scope',
                'type',
                default=self._resolve_scope_value(data, 'owner_scope', 'type', default='global'),
            ),
            target_scope_code=self._resolve_scope_value(
                data,
                'target_scope',
                'code',
                default=self._resolve_scope_value(data, 'owner_scope', 'code'),
            ),
            target_scope_name=self._resolve_scope_value(
                data,
                'target_scope',
                'name',
                default=self._resolve_scope_value(data, 'owner_scope', 'name'),
            ),
            target_scope_path=self._resolve_scope_value(
                data,
                'target_scope',
                'path',
                default=self._resolve_scope_value(data, 'owner_scope', 'path'),
            ),
            access_policy_key=data.get('access_policy_key') or 'form.default',
        )
        self._apply_actor_audit(form, actor, action='create')

        try:
            form = self.repository.save(form)
            initial_schema = data.get('schema')
            draft_version = None
            if initial_schema is not None:
                draft_version = self.version_service.create_draft_version(
                    form_id=form.id,
                    schema=initial_schema,
                    validation_rules=data.get('validation_rules'),
                    submission_contract=data.get('submission_contract'),
                    actor=actor,
                )
            return {
                'form': form,
                'draft_version': draft_version,
            }
        except Exception:
            db.session.rollback()
            raise

    def update_form_identity(self, form_id, data, actor=None):
        """Memperbarui identitas dan metadata utama sebuah form.

        Args:
            form_id (Any): Primary key internal form target.
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.update_form_identity(form_id=..., data=..., actor=...)
        """

        form = self.repository.get_by_id(form_id)
        if not form:
            raise ValueError('Form tidak ditemukan.')
        if not can_update_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengubah form.')

        code = data.get('code')
        slug = data.get('slug')

        if code and self.repository.exists_code(code, exclude_form_id=form.id):
            raise ValueError('Kode form sudah digunakan.')
        if slug and self.repository.exists_slug(slug, exclude_form_id=form.id):
            raise ValueError('Slug form sudah digunakan.')

        for field in [
            'code',
            'slug',
            'name',
            'description',
            'status',
            'visibility',
            'settings',
            'owner_user_id',
            'owner_scope_type',
            'owner_scope_code',
            'owner_scope_name',
            'owner_scope_path',
            'target_scope_type',
            'target_scope_code',
            'target_scope_name',
            'target_scope_path',
            'access_policy_key',
        ]:
            if field in data:
                setattr(form, field, data[field])
        self._apply_actor_audit(form, actor, action='update')
        return self.repository.save(form)

    def archive_form(self, form_id, actor=None):
        """Mengarsipkan form agar tidak lagi aktif dipakai operasional.

        Args:
            form_id (Any): Primary key internal form target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.archive_form(form_id=..., actor=...)
        """

        form = self.repository.get_by_id(form_id)
        if not form:
            raise ValueError('Form tidak ditemukan.')
        if not can_archive_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengarsipkan form.')
        form.status = 'archived'
        self._apply_actor_audit(form, actor, action='update')
        return self.repository.save(form)

    def get_form_detail(self, form_id):
        """Mengambil detail form berdasarkan primary key internal.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_form_detail(form_id=...)
        """

        return self.repository.get_by_id(form_id)

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

    def _resolve_scope_value(self, data, prefix, field, default=None):
        """Helper internal untuk resolve scope value.

        Args:
            data (Any): Payload utama operasi service dalam bentuk dict/JSON-like.
            prefix (Any): Parameter `prefix` untuk operasi resolve scope value.
            field (Any): Parameter `field` untuk operasi resolve scope value.
            default (Any): Parameter `default` untuk operasi resolve scope value.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service._resolve_scope_value(data=..., prefix=..., field=...)
        """

        nested_scope = data.get(prefix)
        if isinstance(nested_scope, dict) and field in nested_scope:
            return nested_scope.get(field)

        flat_key = f'{prefix}_{field}'
        if flat_key in data:
            return data.get(flat_key)

        return default


class FormVersionService(BaseService):
    """Service versioning schema form beserta publish/archive draft.

    Class ini dipakai sebagai lapisan orkestrasi business rule di atas repository
    dan model, sehingga route/controller tidak perlu menyimpan logika domain.

    Example:
        >>> service = FormVersionService()
    """

    def __init__(self, version_repository=None, form_repository=None):
        """Inisialisasi class beserta dependency yang diperlukan.

        Args:
            version_repository (Any): Parameter `version_repository` untuk operasi init.
            form_repository (Any): Parameter `form_repository` untuk operasi init.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service = FormVersionService()
        """

        super().__init__(repository=version_repository or FormVersionRepository())
        self.form_repository = form_repository or FormRepository()

    def create_draft_version(
        self,
        form_id,
        schema,
        actor=None,
        source_version_id=None,
        validation_rules=None,
        submission_contract=None,
    ):
        """Membuat draft version baru atau me-refresh draft aktif dengan schema terbaru.

        Args:
            form_id (Any): Primary key internal form target.
            schema (Any): Schema JSON/Form.io yang dipakai untuk validasi atau versioning.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.
            source_version_id (Any): Parameter `source_version_id` untuk operasi create draft version.
            validation_rules (Any): Parameter `validation_rules` untuk operasi create draft version.
            submission_contract (Any): Parameter `submission_contract` untuk operasi create draft version.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.create_draft_version(form_id=..., schema=..., actor=...)
        """

        form = self.form_repository.get_by_id(form_id)
        if not form:
            raise ValueError('Form tidak ditemukan.')
        if not can_update_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengubah draft form.')

        source_version = None
        if source_version_id is not None:
            source_version = self.repository.get_by_id(source_version_id)
            if not source_version:
                raise ValueError('Source version tidak ditemukan.')
            if source_version.form_id != form_id:
                raise ValueError('Source version tidak sesuai dengan form.')
            if schema is None:
                schema = source_version.schema
            if validation_rules is None:
                validation_rules = source_version.validation_rules
            if submission_contract is None:
                submission_contract = source_version.submission_contract

        if not isinstance(schema, dict):
            raise ValueError('Schema form wajib berupa object/dict.')

        existing_draft = self.repository.get_draft_version(form_id) if hasattr(self.repository, 'get_draft_version') else None
        if existing_draft:
            existing_draft.schema = schema
            if validation_rules is not None:
                existing_draft.validation_rules = validation_rules
            if submission_contract is not None:
                existing_draft.submission_contract = submission_contract
            if source_version:
                existing_draft.notes = f'Cloned from version {source_version.version_number}'
            existing_draft.scope_snapshot = self._build_scope_snapshot(form)
            existing_draft.access_policy_snapshot = self._build_access_policy_snapshot(form)
            self._apply_actor_audit(existing_draft, actor, action='update')
            return self.repository.save(existing_draft)

        version = FormVersion(
            uuid=str(uuid.uuid4()),
            form_id=form_id,
            version_number=self.repository.get_next_version_number(form_id),
            version_label=None,
            schema=schema,
            validation_rules=validation_rules,
            submission_contract=submission_contract,
            scope_snapshot=source_version.scope_snapshot if source_version and source_version.scope_snapshot else self._build_scope_snapshot(form),
            access_policy_snapshot=(
                source_version.access_policy_snapshot
                if source_version and source_version.access_policy_snapshot
                else self._build_access_policy_snapshot(form)
            ),
            status='draft',
            is_published=False,
            notes=f'Cloned from version {source_version.version_number}' if source_version else None,
        )
        self._apply_actor_audit(version, actor, action='create')
        return self.repository.save(version)

    def update_draft_schema(self, version_id, schema, validation_rules=None, actor=None):
        """Memperbarui schema draft version tanpa membuat row version utama baru.

        Args:
            version_id (Any): Primary key internal version target.
            schema (Any): Schema JSON/Form.io yang dipakai untuk validasi atau versioning.
            validation_rules (Any): Parameter `validation_rules` untuk operasi update draft schema.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.update_draft_schema(version_id=..., schema=..., validation_rules=...)
        """

        version = self.repository.get_by_id(version_id)
        if not version:
            raise ValueError('Form version tidak ditemukan.')
        form = self.form_repository.get_by_id(version.form_id) if version.form_id else None
        if not can_update_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengubah draft form.')
        if version.status != 'draft' or version.is_published:
            raise ValueError('Hanya draft version yang boleh diedit.')
        if not isinstance(schema, dict):
            raise ValueError('Schema form wajib berupa object/dict.')

        version.schema = schema
        if validation_rules is not None:
            version.validation_rules = validation_rules
        self._apply_actor_audit(version, actor, action='update')
        return self.repository.save(version)

    def publish_version(self, version_id, actor=None):
        """Mempublish draft version dan menonaktifkan published version lain dalam form yang sama.

        Args:
            version_id (Any): Primary key internal version target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.publish_version(version_id=..., actor=...)
        """

        version = self.repository.get_by_id(version_id)
        if not version:
            raise ValueError('Form version tidak ditemukan.')
        if version.status != 'draft':
            raise ValueError('Hanya draft version yang boleh dipublish.')
        form = self.form_repository.get_by_id(version.form_id)
        if not can_publish_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin publish form.')
        self._validate_schema(version.schema)

        self.repository.unpublish_others(version.form_id, except_version_id=version.id)
        version.status = 'published'
        version.is_published = True
        version.published_at = now_utc()
        form = self.form_repository.get_by_id(version.form_id)
        version.scope_snapshot = self._build_scope_snapshot(form)
        version.access_policy_snapshot = self._build_access_policy_snapshot(form)
        self._apply_actor_audit(version, actor, action='update')
        saved_version = self.repository.save(version)

        if form:
            form.status = 'published'
            self._apply_actor_audit(form, actor, action='update')
            self.form_repository.save(form)

        return saved_version

    def archive_version(self, version_id, actor=None):
        """Mengarsipkan version form tertentu.

        Args:
            version_id (Any): Primary key internal version target.
            actor (Any): User/actor runtime untuk audit trail dan otorisasi, bila tersedia.

        Returns:
            Any: Entity atau ringkasan hasil operasi bisnis yang sudah dipersist.

        Example:
            >>> service.archive_version(version_id=..., actor=...)
        """

        version = self.repository.get_by_id(version_id)
        if not version:
            raise ValueError('Form version tidak ditemukan.')
        version.status = 'archived'
        version.is_published = False
        self._apply_actor_audit(version, actor, action='update')
        return self.repository.save(version)

    def get_published_version(self, form_id):
        """Mengambil version published untuk form tertentu.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_published_version(form_id=...)
        """

        return self.repository.get_published_version(form_id)

    def get_draft_version(self, form_id):
        """Mengambil draft version aktif untuk form tertentu.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service.get_draft_version(form_id=...)
        """

        return self.repository.get_draft_version(form_id)

    def _validate_schema(self, schema):
        """Helper internal untuk validate schema.

        Args:
            schema (Any): Schema JSON/Form.io yang dipakai untuk validasi atau versioning.

        Returns:
            Any: Nilai hasil eksekusi fungsi service.

        Example:
            >>> service._validate_schema(schema=...)
        """

        if not isinstance(schema, dict):
            raise ValueError('Schema form wajib berupa object/dict.')
        if 'components' not in schema:
            raise ValueError('Schema form wajib memiliki key components.')
        return True

    def _build_scope_snapshot(self, form):
        """Helper internal untuk build scope snapshot.

        Args:
            form (Any): Entity form yang sudah di-resolve sebelumnya.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service._build_scope_snapshot(form=...)
        """

        if not form:
            return None

        return {
            'owner_scope': {
                'type': getattr(form, 'owner_scope_type', None),
                'code': getattr(form, 'owner_scope_code', None),
                'name': getattr(form, 'owner_scope_name', None),
                'path': getattr(form, 'owner_scope_path', None),
            },
            'target_scope': {
                'type': getattr(form, 'target_scope_type', None),
                'code': getattr(form, 'target_scope_code', None),
                'name': getattr(form, 'target_scope_name', None),
                'path': getattr(form, 'target_scope_path', None),
            },
        }

    def _build_access_policy_snapshot(self, form):
        """Helper internal untuk build access policy snapshot.

        Args:
            form (Any): Entity form yang sudah di-resolve sebelumnya.

        Returns:
            Any: Struktur data hasil olahan service sesuai kebutuhan caller.

        Example:
            >>> service._build_access_policy_snapshot(form=...)
        """

        if not form:
            return None

        return {
            'key': getattr(form, 'access_policy_key', None),
        }

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
