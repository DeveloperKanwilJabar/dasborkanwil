from app import create_app


def test_form_repository_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.repositories import FormRepository, FormVersionRepository

        form_repository = FormRepository()
        version_repository = FormVersionRepository()

        for method_name in [
            'exists_code',
            'exists_slug',
            'get_by_slug',
            'get_active_by_slug',
            'list_by_status',
        ]:
            assert callable(getattr(form_repository, method_name))

        for method_name in [
            'get_latest_version',
            'get_next_version_number',
            'get_published_version',
            'list_versions',
            'unpublish_others',
        ]:
            assert callable(getattr(version_repository, method_name))


def test_submission_repository_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.repositories import (
            ReportingPeriodRepository,
            SubmissionEventRepository,
            SubmissionRepository,
        )

        period_repository = ReportingPeriodRepository()
        submission_repository = SubmissionRepository()
        event_repository = SubmissionEventRepository()

        for method_name in [
            'get_active_by_year',
            'get_by_code',
            'list_by_year',
            'list_by_type',
        ]:
            assert callable(getattr(period_repository, method_name))

        for method_name in [
            'get_by_number',
            'list_by_form',
            'list_by_reporting_year',
            'list_by_reporting_period',
            'list_for_analytics',
            'get_last_submitted_at',
        ]:
            assert callable(getattr(submission_repository, method_name))

        for method_name in [
            'list_by_submission',
            'list_by_event_type',
        ]:
            assert callable(getattr(event_repository, method_name))


def test_form_service_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.form.services import FormService, FormVersionService

        form_service = FormService()
        version_service = FormVersionService()

        for method_name in [
            'create_form',
            'update_form_identity',
            'archive_form',
            'get_form_detail',
        ]:
            assert callable(getattr(form_service, method_name))

        for method_name in [
            'create_draft_version',
            'update_draft_schema',
            'publish_version',
            'archive_version',
            'get_published_version',
        ]:
            assert callable(getattr(version_service, method_name))


def test_submission_service_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.services import SubmissionService

        submission_service = SubmissionService()

        for method_name in [
            'create_draft',
            'submit',
            'validate_payload',
            'resolve_reporting_period',
            'add_event',
            'get_data_freshness',
        ]:
            assert callable(getattr(submission_service, method_name))


def test_submission_service_get_data_freshness_uses_repository_last_submitted_at():
    app = create_app('testing')

    with app.app_context():
        from app.modules.submission.services import SubmissionService

        class StubSubmissionRepository:
            def __init__(self):
                self.called_with = None

            def get_last_submitted_at(self, **filters):
                self.called_with = filters
                return '2026-05-07T14:20:00+07:00'

        stub_repository = StubSubmissionRepository()
        submission_service = SubmissionService(submission_repository=stub_repository)

        result = submission_service.get_data_freshness(
            form_id=10,
            reporting_year=2026,
            reporting_period_id=3,
        )

        assert stub_repository.called_with == {
            'form_id': 10,
            'reporting_year': 2026,
            'reporting_period_id': 3,
            'statuses': None,
        }
        assert result == {
            'data_last_updated_at': '2026-05-07T14:20:00+07:00',
            'source': 'submissions.submitted_at',
            'form_id': 10,
            'reporting_year': 2026,
            'reporting_period_id': 3,
        }
