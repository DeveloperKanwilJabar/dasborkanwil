from app import create_app


def test_swagger_ui_route_is_registered_and_accessible():
    app = create_app('testing')
    client = app.test_client()

    response = client.get('/api/docs/')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'swagger-ui' in html.lower() or 'flasgger' in html.lower()


def test_openapi_json_contains_key_project_routes():
    app = create_app('testing')
    client = app.test_client()

    response = client.get('/api/docs/openapi.json')

    assert response.status_code == 200
    payload = response.get_json()
    paths = payload['paths']
    assert '/api/v1/forms' in paths
    assert '/api/v1/forms/{form_id}' in paths
    assert '/api/v1/forms/{form_id}/submissions' in paths
    assert '/api/v1/analytics/reports' in paths
    assert '/api/v1/registry-resources/{registry_slug}/options' in paths
