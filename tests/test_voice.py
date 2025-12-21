def test_voice_info(client):
    resp = client.get('/voice/')
    assert resp.status_code == 200
    assert resp.get_json() == {'module': 'voice', 'status': 'ok'}


def test_voice_health(client):
    resp = client.get('/voice/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}
