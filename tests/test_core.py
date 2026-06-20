def test_index(client):
    resp = client.get('/api/v1/core/')
    assert resp.status_code == 200
    assert "Hello World" in resp.text


def test_core_health(client):
    resp = client.get('/api/v1/core/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}

