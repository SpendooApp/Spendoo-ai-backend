def test_forecasting_info(client):
    resp = client.get('/forecast/')
    assert resp.status_code == 200
    assert resp.get_json() == {'module': 'forecasting', 'status': 'ok'}


def test_forecasting_health(client):
    resp = client.get('/forecast/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}
