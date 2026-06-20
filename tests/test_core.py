def test_index(client):
    resp = client.get('/api/v1/core/')
    assert resp.status_code == 200
    assert "Hello World" in resp.text


def test_core_health(client):
    resp = client.get('/api/v1/core/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


def test_ip_restriction_middleware():
    import os
    from fastapi.testclient import TestClient
    from app import create_app

    original_deploy = os.environ.get("SPENDOO_DEPLOY")
    os.environ["SPENDOO_DEPLOY"] = "true"

    try:
        app = create_app()
        client = TestClient(app)

        # Request with a blocked client IP
        resp = client.get('/api/v1/core/', headers={"x-forwarded-for": "192.168.1.100"})
        assert resp.status_code == 403
        assert resp.json() == {"detail": "Forbidden: IP 192.168.1.100 not allowed"}

        # Request with default allowed client IPs
        resp_allowed = client.get('/api/v1/core/', headers={"x-forwarded-for": "127.0.0.1"})
        assert resp_allowed.status_code == 200

        # Request with Docker subnet allowed IPs
        resp_subnet1 = client.get('/api/v1/core/', headers={"x-forwarded-for": "172.17.0.2"})
        assert resp_subnet1.status_code == 200

        # Request with custom/other Docker subnet allowed IPs
        resp_subnet2 = client.get('/api/v1/core/', headers={"x-forwarded-for": "172.18.0.5"})
        assert resp_subnet2.status_code == 200
    finally:
        if original_deploy is not None:
            os.environ["SPENDOO_DEPLOY"] = original_deploy
        else:
            del os.environ["SPENDOO_DEPLOY"]

