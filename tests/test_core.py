def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Hello World' in resp.data


def test_core_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}
