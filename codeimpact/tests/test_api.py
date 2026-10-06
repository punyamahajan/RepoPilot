"""API boundary checks run in the CodeImpact environment/container."""
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from codeimpact import api


def test_input_validation_and_root_boundary():
    client = TestClient(api.app)
    assert client.post('/api/analyses', json={}).status_code == 400
    assert client.post('/api/analyses', json={'description': 'x'*20001}).status_code == 422
    assert client.get('/api/repository', params={'repository': '../'}).status_code == 400
    assert client.post('/api/analyses', json={'description':'change code'}, headers={'Origin':'https://untrusted.example'}).status_code == 403


def test_report_job_and_download():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'fee.py').write_text('def calculate_fee(amount): return amount * .03')
        with patch.object(api, 'ALLOWED_ROOT', root), patch.object(api, 'STATE', root / '.codeimpact'):
            client = TestClient(api.app)
            response = client.post('/api/analyses', json={'changed_files':['fee.py'], 'semantic':False, 'use_llm':False})
            assert response.status_code == 202
            job_id = response.json()['id']
            for _ in range(100):
                job = client.get('/api/jobs/' + job_id).json()
                if job['status'] in {'completed','failed'}:
                    break
                time.sleep(.05)
            assert job['status'] == 'completed', job
            report = client.get('/api/reports/' + job['report_id']).json()
            assert report['changed_files'] == ['fee.py']
            assert client.get('/api/reports/' + job['report_id'] + '/markdown').status_code == 200
            assert client.get('/api/reports').json()[0]['id'] == report['id']


def test_unknown_report_and_job():
    client = TestClient(api.app)
    assert client.get('/api/reports/not-a-report').status_code == 404
    assert client.get('/api/jobs/not-a-job').status_code == 404
