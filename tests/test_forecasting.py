def test_forecasting_info(client):
    resp = client.get('/api/v1/forecasting/')
    assert resp.status_code == 200
    assert resp.json() == {'module': 'forecasting', 'status': 'ok'}


def test_forecasting_health(client):
    resp = client.get('/api/v1/forecasting/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}

