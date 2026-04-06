from fastapi.testclient import TestClient

from interactive_seminar.app import create_app
from interactive_seminar.notebook_loader import load_manifest


class ApiFakeRunner:
    def run(
        self,
        *,
        credentials,
        model,
        prompt_or_messages,
        system_prompt='',
        prefill='',
        stop_sequences=None,
    ):
        return 'fake-response'



def test_healthcheck_endpoint_exists():
    client = TestClient(create_app())
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}



def test_manifest_endpoint_returns_parts():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    client = TestClient(create_app(manifest=manifest, runner=ApiFakeRunner()))
    response = client.get('/api/manifest')
    assert response.status_code == 200
    body = response.json()
    assert 'parts' in body
    assert any(part['title'] == 'Part 1' for part in body['parts'])



def test_sandbox_endpoint_returns_response_shape():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    client = TestClient(create_app(manifest=manifest, runner=ApiFakeRunner()))
    payload = {
        'credentials': 'test-key',
        'model': 'GigaChat',
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'system_prompt': '',
        'prefill': '',
        'stop_sequences': [],
    }
    response = client.post('/api/run/sandbox', json=payload)
    assert response.status_code == 200
    assert response.json()['response'] == 'fake-response'


def test_root_serves_html_shell():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    client = TestClient(create_app(manifest=manifest, runner=ApiFakeRunner()))
    response = client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert 'Interactive Prompt Engineering Seminar' in response.text


def test_root_places_runner_before_content():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    client = TestClient(create_app(manifest=manifest, runner=ApiFakeRunner()))
    response = client.get('/')
    html = response.text
    runner_index = html.index('class="runner-panel"')
    content_index = html.index('class="content-panel"')
    assert runner_index < content_index
