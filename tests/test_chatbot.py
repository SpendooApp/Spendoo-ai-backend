def test_chatbot_info(client):
    resp = client.get('/chatbot/')
    assert resp.status_code == 200
    assert resp.get_json() == {'module': 'chatbot', 'status': 'ok'}


def test_chatbot_health(client):
    resp = client.get('/chatbot/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}
