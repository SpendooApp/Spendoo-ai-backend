def test_chatbot_info(client):
    resp = client.get('/api/v1/chatbot/')
    assert resp.status_code == 200
    assert resp.json() == {'module': 'chatbot', 'status': 'ok'}


def test_chatbot_health(client):
    resp = client.get('/api/v1/chatbot/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}

