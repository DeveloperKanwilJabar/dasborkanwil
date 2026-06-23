from types import SimpleNamespace

import pytest

from app import create_app


def route_rules(app):
    return {rule.rule: sorted(rule.methods) for rule in app.url_map.iter_rules()}


def make_form(**overrides):
    defaults = {
        'id': 1,
        'uuid': 'form-uuid',
        'code': 'FORM-API',
        'slug': 'form-api',
        'name': 'Form API',
        'description': None,
        'status': 'draft',
        'visibility': 'internal',
        'settings': None,
        'owner_user_id': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_form_version(**overrides):
    defaults = {
        'id': 1,
        'uuid': 'version-uuid',
        'form_id': 1,
        'version_number': 1,
        'version_label': None,
        'schema': {'components': []},
        'validation_rules': None,
        'submission_contract': None,
        'status': 'draft',
        'is_published': False,
        'published_at': None,
        'notes': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_submission(**overrides):
    defaults = {
        'id': 1,
        'uuid': 'submission-uuid',
        'submission_number': 'SUB-2026-ABC123',
        'form_id': 1,
        'form_version_id': 1,
        'reporting_year': 2026,
        'reporting_period_id': None,
        'status': 'submitted',
        'submitted_at': None,
        'payload': {'nama': 'Budi'},
        'meta': {'source': 'web'},
        'validation_snapshot': {'is_valid': True},
        'submitted_by': None,
        'submitted_by_uuid': None,
        'source_type': 'web',
        'source_ref': None,
        'created_at': None,
        'updated_at': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def assert_validation_error(response, expected_message):
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert expected_message in payload['message']
    assert payload['data']['error_type'] == 'validation_error'


def test_form_builder_api_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/api/v1/forms',
        '/api/v1/forms/<int:form_id>',
        '/api/v1/forms/<int:form_id>/versions/draft',
        '/api/v1/form-versions/<int:version_id>/draft-schema',
        '/api/v1/form-versions/<int:version_id>/publish',
    ]

    for route in expected_routes:
        assert route in rules


def test_submission_api_routes_are_registered():
    app = create_app('testing')
    rules = route_rules(app)

    expected_routes = [
        '/api/v1/forms/<int:form_id>/submissions',
        '/api/v1/submissions',
        '/api/v1/submissions/<int:submission_id>',
        '/api/v1/submissions/freshness',
    ]

    for route in expected_routes:
        assert route in rules


def test_post_forms_returns_authorization_error_when_service_denies(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubFormService:
        def create_form(self, data, actor=None):
            raise PermissionError('Actor tidak memiliki izin membuat form.')

    monkeypatch.setattr('app.api.v1.forms.routes.FormService', StubFormService)

    response = client.post(
        '/api/v1/forms',
        json={
            'code': 'FORM-API',
            'slug': 'form-api',
            'name': 'Form API',
            'schema': {'components': []},
        },
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload['success'] is False
    assert payload['data']['error_type'] == 'authorization_error'
    assert 'izin membuat form' in payload['message']



def test_post_forms_returns_created_form_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubFormService:
        def create_form(self, data, actor=None):
            return {
                'form': make_form(code=data['code'], slug=data['slug'], name=data['name']),
                'draft_version': make_form_version(schema=data['schema']),
            }

    monkeypatch.setattr('app.api.v1.forms.routes.FormService', StubFormService)

    response = client.post(
        '/api/v1/forms',
        json={
            'code': 'FORM-API',
            'slug': 'form-api',
            'name': 'Form API',
            'schema': {'components': []},
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['form']['code'] == 'FORM-API'
    assert payload['data']['draft_version']['schema'] == {'components': []}


def test_patch_draft_schema_returns_autosaved_version_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubFormVersionService:
        def update_draft_schema(self, version_id, schema, validation_rules=None, actor=None):
            return make_form_version(
                id=version_id,
                schema=schema,
                validation_rules=validation_rules,
            )

    monkeypatch.setattr('app.api.v1.forms.routes.FormVersionService', StubFormVersionService)

    response = client.patch(
        '/api/v1/form-versions/1/draft-schema',
        json={
            'schema': {'components': [{'key': 'nama'}]},
            'validation_rules': {'required': ['nama']},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['draft_version']['id'] == 1
    assert payload['data']['draft_version']['schema'] == {'components': [{'key': 'nama'}]}
    assert payload['data']['autosaved_at'] is not None


def test_publish_version_returns_published_version_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubFormVersionService:
        def publish_version(self, version_id, actor=None):
            return make_form_version(
                id=version_id,
                status='published',
                is_published=True,
            )

    monkeypatch.setattr('app.api.v1.forms.routes.FormVersionService', StubFormVersionService)

    response = client.post('/api/v1/form-versions/1/publish', json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['published_version']['id'] == 1
    assert payload['data']['published_version']['status'] == 'published'
    assert payload['data']['published_version']['is_published'] is True


def test_submit_form_returns_authorization_error_when_service_denies(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubSubmissionService:
        def submit(
            self,
            form_id,
            payload,
            actor=None,
            context=None,
            reporting_year=None,
            reporting_period_id=None,
        ):
            raise PermissionError('Actor tidak memiliki izin mengirim submission untuk form ini.')

    monkeypatch.setattr('app.api.v1.submissions.routes.SubmissionService', StubSubmissionService)

    response = client.post(
        '/api/v1/forms/1/submissions',
        json={
            'payload': {'nama': 'Budi'},
            'reporting_year': 2026,
        },
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload['success'] is False
    assert payload['data']['error_type'] == 'authorization_error'
    assert 'izin mengirim submission' in payload['message']



def test_submit_form_returns_submission_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubSubmissionService:
        def submit(
            self,
            form_id,
            payload,
            actor=None,
            context=None,
            reporting_year=None,
            reporting_period_id=None,
        ):
            return make_submission(
                form_id=form_id,
                payload=payload,
                reporting_year=reporting_year,
                reporting_period_id=reporting_period_id,
                meta=context.get('meta'),
                source_type=context.get('source_type'),
            )

    monkeypatch.setattr('app.api.v1.submissions.routes.SubmissionService', StubSubmissionService)

    response = client.post(
        '/api/v1/forms/1/submissions',
        json={
            'payload': {'nama': 'Budi'},
            'reporting_year': 2026,
            'meta': {'source': 'web'},
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['submission']['form_id'] == 1
    assert payload['data']['submission']['status'] == 'submitted'
    assert payload['data']['submission']['reporting_year'] == 2026
    assert payload['data']['submission_number']


def test_list_submissions_returns_grid_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubSubmissionService:
        def list_submissions(self, actor=None, form_id=None, reporting_year=None, reporting_period_id=None, statuses=None):
            assert form_id == 1
            return [make_submission(id=9, form_id=form_id)]

    monkeypatch.setattr('app.api.v1.submissions.routes.SubmissionService', StubSubmissionService)

    response = client.get('/api/v1/submissions?form_id=1')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data'][0]['id'] == 9
    assert payload['data'][0]['permissions']['can_edit'] is True


def test_update_submission_calls_service_and_returns_freshness_ready_payload(monkeypatch):
    app = create_app('testing')
    client = app.test_client()

    class StubSubmissionService:
        def update_submission(self, submission_id, payload, actor=None, refresh_submitted_at=True):
            assert submission_id == 9
            assert payload == {'nama': 'Siti'}
            assert refresh_submitted_at is True
            return make_submission(id=submission_id, payload=payload)

    monkeypatch.setattr('app.api.v1.submissions.routes.SubmissionService', StubSubmissionService)

    response = client.put('/api/v1/submissions/9', json={'payload': {'nama': 'Siti'}, 'refresh_submitted_at': True})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['submission']['payload'] == {'nama': 'Siti'}


@pytest.mark.parametrize(
    'endpoint,method,patch_target,service_method,expected_message',
    [
        (
            '/api/v1/forms',
            'post',
            'app.api.v1.forms.routes.FormService',
            'create_form',
            'Kode form wajib diisi.',
        ),
        (
            '/api/v1/form-versions/1/draft-schema',
            'patch',
            'app.api.v1.forms.routes.FormVersionService',
            'update_draft_schema',
            'Schema form wajib berupa object/dict.',
        ),
        (
            '/api/v1/form-versions/1/publish',
            'post',
            'app.api.v1.forms.routes.FormVersionService',
            'publish_version',
            'Schema form wajib memiliki key components.',
        ),
        (
            '/api/v1/forms/1/submissions',
            'post',
            'app.api.v1.submissions.routes.SubmissionService',
            'submit',
            'Payload submission wajib berupa object/dict.',
        ),
    ],
)
def test_api_validation_errors_return_standard_400(
    monkeypatch,
    endpoint,
    method,
    patch_target,
    service_method,
    expected_message,
):
    app = create_app('testing')
    client = app.test_client()

    class StubService:
        pass

    def raise_validation_error(*args, **kwargs):
        raise ValueError(expected_message)

    setattr(StubService, service_method, raise_validation_error)
    monkeypatch.setattr(patch_target, StubService)

    response = getattr(client, method)(endpoint, json={})

    assert_validation_error(response, expected_message)
