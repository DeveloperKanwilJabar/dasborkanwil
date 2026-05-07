from types import SimpleNamespace

import pytest

from app import create_app
from app.modules.form.models import Form, FormVersion
from app.modules.submission.models import SubmissionEvent

from tests.test_form_submission_service_behaviors import (
    SaveMixin,
    StubFormRepository,
    StubPeriodRepository,
    StubSubmissionEventRepository,
    StubSubmissionRepository,
    StubVersionRepository,
)


class StubNoPublishedVersionRepository:
    def get_published_version(self, form_id):
        return None


class StubInvalidPayloadSubmissionServiceRepository(StubSubmissionRepository):
    pass


def test_publish_version_rejects_invalid_schema_without_components():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.services import FormVersionService

        form = Form(id=10, code='FORM', slug='form', name='Form', status='draft')
        version = FormVersion(
            id=20,
            form_id=10,
            version_number=1,
            schema={'display': 'form'},
            status='draft',
            is_published=False,
        )
        version_repository = StubVersionRepository(version=version)
        form_repository = StubFormRepository(form=form)
        service = FormVersionService(
            version_repository=version_repository,
            form_repository=form_repository,
        )

        with pytest.raises(ValueError, match='components'):
            service.publish_version(20)

        assert version.status == 'draft'
        assert version.is_published is False
        assert version_repository.unpublished_args is None


def test_submit_rejects_form_without_published_version():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.services import SubmissionService

        form = Form(id=10, code='FORM', slug='form', name='Form', status='draft')
        service = SubmissionService(
            submission_repository=StubSubmissionRepository(),
            event_repository=StubSubmissionEventRepository(),
            form_repository=StubFormRepository(form=form),
            version_repository=StubNoPublishedVersionRepository(),
            period_repository=StubPeriodRepository(),
        )

        with pytest.raises(ValueError, match='published version'):
            service.submit(form_id=10, payload={'nama': 'Budi'})


def test_resolve_reporting_period_uses_actor_active_year():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.services import SubmissionService

        service = SubmissionService(
            period_repository=StubPeriodRepository(),
        )
        actor = SimpleNamespace(id=7, uuid='actor-uuid', settings={'active_year': 2026})

        result = service.resolve_reporting_period(actor=actor)

        assert result == {
            'reporting_period_id': 30,
            'reporting_year': 2026,
        }


def test_submit_records_validation_failed_event_when_payload_invalid():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.services import SubmissionService

        form = Form(id=10, code='FORM', slug='form', name='Form', status='published')
        published_version = FormVersion(
            id=20,
            form_id=10,
            version_number=1,
            schema={'components': []},
            status='published',
            is_published=True,
        )
        event_repository = StubSubmissionEventRepository()
        service = SubmissionService(
            submission_repository=StubInvalidPayloadSubmissionServiceRepository(),
            event_repository=event_repository,
            form_repository=StubFormRepository(form=form),
            version_repository=StubVersionRepository(published_version=published_version),
            period_repository=StubPeriodRepository(),
        )

        with pytest.raises(ValueError, match='Payload submission wajib berupa object'):
            service.submit(form_id=10, payload=['bukan', 'dict'])

        assert len(event_repository.saved) == 1
        event = event_repository.saved[0]
        assert isinstance(event, SubmissionEvent)
        assert event.submission_id is None
        assert event.event_type == 'validation_failed'
        assert event.context['error'] == 'Payload submission wajib berupa object/dict.'
