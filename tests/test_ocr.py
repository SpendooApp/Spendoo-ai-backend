def test_ocr_info(client):
    resp = client.get('/ocr/')
    assert resp.status_code == 200
    assert resp.get_json() == {'module': 'ocr', 'status': 'ok'}


def test_ocr_health(client):
    resp = client.get('/ocr/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}
