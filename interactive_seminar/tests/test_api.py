from fastapi.testclient import TestClient

from interactive_seminar.app import create_app


def test_healthcheck_endpoint_exists():
    client = TestClient(create_app())
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
