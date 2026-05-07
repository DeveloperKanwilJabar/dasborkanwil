import uuid

from app.core.access import can_archive_form, can_create_form, can_publish_form, can_update_form
from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc

from .models import Form, FormVersion
from .repositories import FormRepository, FormVersionRepository


class FormService(BaseService):
    def __init__(self, form_repository=None, version_service=None):
        super().__init__(repository=form_repository or FormRepository())
        self.version_service = version_service or FormVersionService()

    def create_form(self, data, actor=None):
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
        form = self.repository.get_by_id(form_id)
        if not form:
            raise ValueError('Form tidak ditemukan.')
        if not can_archive_form(actor, form):
            raise PermissionError('Actor tidak memiliki izin mengarsipkan form.')
        form.status = 'archived'
        self._apply_actor_audit(form, actor, action='update')
        return self.repository.save(form)

    def get_form_detail(self, form_id):
        return self.repository.get_by_id(form_id)

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

    def _resolve_scope_value(self, data, prefix, field, default=None):
        nested_scope = data.get(prefix)
        if isinstance(nested_scope, dict) and field in nested_scope:
            return nested_scope.get(field)

        flat_key = f'{prefix}_{field}'
        if flat_key in data:
            return data.get(flat_key)

        return default


class FormVersionService(BaseService):
    def __init__(self, version_repository=None, form_repository=None):
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
        version = self.repository.get_by_id(version_id)
        if not version:
            raise ValueError('Form version tidak ditemukan.')
        version.status = 'archived'
        version.is_published = False
        self._apply_actor_audit(version, actor, action='update')
        return self.repository.save(version)

    def get_published_version(self, form_id):
        return self.repository.get_published_version(form_id)

    def get_draft_version(self, form_id):
        return self.repository.get_draft_version(form_id)

    def _validate_schema(self, schema):
        if not isinstance(schema, dict):
            raise ValueError('Schema form wajib berupa object/dict.')
        if 'components' not in schema:
            raise ValueError('Schema form wajib memiliki key components.')
        return True

    def _build_scope_snapshot(self, form):
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
        if not form:
            return None

        return {
            'key': getattr(form, 'access_policy_key', None),
        }

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
