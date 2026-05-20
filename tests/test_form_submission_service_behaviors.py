from types import SimpleNamespace

import pytest

from app import create_app
from app.modules.form.models import Form, FormVersion
from app.modules.submission.models import Submission, SubmissionEvent


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


class StubFormRepository(SaveMixin):
    def __init__(self, form=None):
        super().__init__()
        self.form = form
        self.exists_code_value = False
        self.exists_slug_value = False

    def exists_code(self, code, exclude_form_id=None):
        return self.exists_code_value

    def exists_slug(self, slug, exclude_form_id=None):
        return self.exists_slug_value

    def get_by_id(self, form_id):
        if self.form and self.form.id == form_id:
            return self.form
        return None


class StubVersionRepository(SaveMixin):
    def __init__(self, version=None, published_version=None):
        super().__init__()
        self.version = version
        self.published_version = published_version
        self.unpublished_args = None

    def get_by_id(self, version_id):
        if self.version and self.version.id == version_id:
            return self.version
        return None

    def get_next_version_number(self, form_id):
        return 2

    def get_published_version(self, form_id):
        return self.published_version

    def unpublish_others(self, form_id, except_version_id=None):
        self.unpublished_args = {
            'form_id': form_id,
            'except_version_id': except_version_id,
        }
        return []


class StubDraftVersionService:
    def __init__(self):
        self.called_with = None

    def create_draft_version(self, **kwargs):
        self.called_with = kwargs
        return FormVersion(
            id=11,
            form_id=kwargs['form_id'],
            version_number=1,
            schema=kwargs['schema'],
            status='draft',
        )


class StubPeriodRepository:
    def get_by_id(self, reporting_period_id):
        return None

    def get_active_by_year(self, year=None):
        return SimpleNamespace(id=30, year=year)


class StubSubmissionRepository(SaveMixin):
    pass


class StubSubmissionEventRepository(SaveMixin):
    pass


def test_create_form_returns_form_and_initial_draft_version():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.services import FormService

        form_repository = StubFormRepository()
        version_service = StubDraftVersionService()
        service = FormService(
            form_repository=form_repository,
            version_service=version_service,
        )
        actor = SimpleNamespace(
            id=7,
            uuid='actor-uuid',
            roles=['admin_lintas_bagian'],
            settings={
                'scope': {
                    'type': 'kanwil',
                    'code': 'kanwil-jabar',
                    'name': 'Kanwil Jawa Barat',
                    'path': ['kanwil-jabar'],
                },
            },
        )

        result = service.create_form(
            {
                'code': 'FRM-LAPORAN',
                'slug': 'laporan',
                'name': 'Laporan',
                'schema': {'components': []},
                'owner_scope_type': 'unit',
                'owner_scope_code': 'ki',
                'owner_scope_name': 'Kekayaan Intelektual',
                'owner_scope_path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
                'target_scope_type': 'division',
                'target_scope_code': 'divisi-pelayanan-hukum',
                'target_scope_name': 'Divisi Pelayanan Hukum',
                'target_scope_path': ['kanwil-jabar', 'divisi-pelayanan-hukum'],
                'access_policy_key': 'form.division_collaborative',
            },
            actor=actor,
        )

        assert result['form'].id == 1
        assert result['form'].code == 'FRM-LAPORAN'
        assert result['form'].created_by == 7
        assert result['form'].owner_scope_type == 'unit'
        assert result['form'].owner_scope_code == 'ki'
        assert result['form'].target_scope_type == 'division'
        assert result['form'].target_scope_code == 'divisi-pelayanan-hukum'
        assert result['form'].access_policy_key == 'form.division_collaborative'
        assert result['draft_version'].form_id == 1
        assert result['draft_version'].schema == {'components': []}
        assert version_service.called_with['actor'] is actor


def test_create_draft_version_can_clone_from_source_version_when_schema_not_provided():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.services import FormVersionService

        form = Form(id=10, code='FORM', slug='form', name='Form')
        source_version = FormVersion(
            id=20,
            form_id=10,
            version_number=1,
            schema={'components': [{'key': 'nama'}]},
            validation_rules={'required': ['nama']},
            submission_contract={'mode': 'default'},
            status='published',
            is_published=True,
        )
        version_repository = StubVersionRepository(version=source_version)
        form_repository = StubFormRepository(form=form)
        service = FormVersionService(
            version_repository=version_repository,
            form_repository=form_repository,
        )

        draft_version = service.create_draft_version(
            form_id=10,
            schema=None,
            source_version_id=20,
        )

        assert draft_version.form_id == 10
        assert draft_version.version_number == 2
        assert draft_version.schema == {'components': [{'key': 'nama'}]}
        assert draft_version.validation_rules == {'required': ['nama']}
        assert draft_version.submission_contract == {'mode': 'default'}
        assert draft_version.status == 'draft'
        assert draft_version.is_published is False


def test_publish_version_marks_version_published_and_parent_form_published():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.services import FormVersionService

        form = Form(
            id=10,
            code='FORM',
            slug='form',
            name='Form',
            status='draft',
            owner_scope_type='unit',
            owner_scope_code='ki',
            owner_scope_name='Kekayaan Intelektual',
            owner_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            target_scope_type='division',
            target_scope_code='divisi-pelayanan-hukum',
            target_scope_name='Divisi Pelayanan Hukum',
            target_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum'],
            access_policy_key='form.division_collaborative',
        )
        version = FormVersion(
            id=20,
            form_id=10,
            version_number=1,
            schema={'components': []},
            status='draft',
            is_published=False,
        )
        version_repository = StubVersionRepository(version=version)
        form_repository = StubFormRepository(form=form)
        service = FormVersionService(
            version_repository=version_repository,
            form_repository=form_repository,
        )

        published_version = service.publish_version(20)

        assert version_repository.unpublished_args == {
            'form_id': 10,
            'except_version_id': 20,
        }
        assert published_version.status == 'published'
        assert published_version.is_published is True
        assert published_version.published_at is not None
        assert published_version.scope_snapshot == {
            'owner_scope': {
                'type': 'unit',
                'code': 'ki',
                'name': 'Kekayaan Intelektual',
                'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            },
            'target_scope': {
                'type': 'division',
                'code': 'divisi-pelayanan-hukum',
                'name': 'Divisi Pelayanan Hukum',
                'path': ['kanwil-jabar', 'divisi-pelayanan-hukum'],
            },
        }
        assert published_version.access_policy_snapshot == {
            'key': 'form.division_collaborative',
        }
        assert form.status == 'published'
        assert form_repository.saved[-1] is form


def test_create_form_rejects_actor_without_authoring_permission():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.services import FormService

        form_repository = StubFormRepository()
        version_service = StubDraftVersionService()
        service = FormService(
            form_repository=form_repository,
            version_service=version_service,
        )
        actor = SimpleNamespace(
            id=9,
            uuid='pegawai-uuid',
            roles=['pegawai_unit'],
            settings={
                'scope': {
                    'type': 'unit',
                    'code': 'ki',
                    'name': 'Kekayaan Intelektual',
                    'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
                },
            },
        )

        with pytest.raises(PermissionError, match='tidak memiliki izin membuat form'):
            service.create_form(
                {
                    'code': 'FRM-TERLARANG',
                    'slug': 'frm-terlarang',
                    'name': 'Form Terlarang',
                },
                actor=actor,
            )



def test_submit_creates_submission_and_validation_passed_and_submitted_events():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.services import SubmissionService

        form = Form(
            id=10,
            code='FORM',
            slug='form',
            name='Form',
            status='published',
            owner_scope_type='division',
            owner_scope_code='divisi-pelayanan-hukum',
            owner_scope_name='Divisi Pelayanan Hukum',
            owner_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum'],
            target_scope_type='unit',
            target_scope_code='ki',
            target_scope_name='Kekayaan Intelektual',
            target_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            access_policy_key='submission.unit_owned',
        )
        published_version = FormVersion(
            id=20,
            form_id=10,
            version_number=1,
            schema={'components': []},
            status='published',
            is_published=True,
        )
        submission_repository = StubSubmissionRepository()
        event_repository = StubSubmissionEventRepository()
        service = SubmissionService(
            submission_repository=submission_repository,
            event_repository=event_repository,
            form_repository=StubFormRepository(form=form),
            version_repository=StubVersionRepository(published_version=published_version),
            period_repository=StubPeriodRepository(),
        )
        actor = SimpleNamespace(
            id=7,
            uuid='actor-uuid',
            roles=['pegawai_unit'],
            settings={
                'active_year': 2026,
                'scope': {
                    'type': 'unit',
                    'code': 'ki',
                    'name': 'Kekayaan Intelektual',
                    'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
                },
            },
        )

        submission = service.submit(
            form_id=10,
            payload={'nama': 'Budi'},
            actor=actor,
            context={
                'source_type': 'web',
                'subject': {
                    'type': 'employee',
                    'ref_id': 99,
                    'ref_uuid': 'employee-uuid',
                    'ref_code': 'EMP-99',
                    'ref_name': 'Budi',
                },
            },
        )

        assert isinstance(submission, Submission)
        assert submission.id == 1
        assert submission.status == 'submitted'
        assert submission.submitted_at is not None
        assert submission.form_id == 10
        assert submission.form_version_id == 20
        assert submission.reporting_year == 2026
        assert submission.reporting_period_id == 30
        assert submission.submitted_by == 7
        assert submission.source_type == 'web'
        assert submission.owner_scope_type == 'unit'
        assert submission.owner_scope_code == 'ki'
        assert submission.owner_scope_name == 'Kekayaan Intelektual'
        assert submission.owner_scope_path == ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki']
        assert submission.subject_type == 'employee'
        assert submission.subject_ref_id == 99
        assert submission.subject_ref_uuid == 'employee-uuid'
        assert submission.subject_ref_code == 'EMP-99'
        assert submission.subject_ref_name == 'Budi'
        assert submission.access_policy_key == 'submission.unit_owned'
        assert submission.validation_snapshot['is_valid'] is True

        event_types = [event.event_type for event in event_repository.saved]
        assert event_types == ['validation_passed', 'submitted']
        assert all(isinstance(event, SubmissionEvent) for event in event_repository.saved)
