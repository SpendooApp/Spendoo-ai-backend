def test_index(client):
    resp = client.get('/api/v1/core/')
    assert resp.status_code == 200
    assert "Hello World" in resp.text


def test_core_health(client):
    resp = client.get('/api/v1/core/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


def test_hmac_signing_middleware():
    import os
    import time
    import hmac
    import hashlib
    from fastapi.testclient import TestClient
    from app import create_app

    original_deploy = os.environ.get("SPENDOO_DEPLOY")
    original_secret = os.environ.get("HMAC_SECRET_KEY")
    os.environ["SPENDOO_DEPLOY"] = "true"
    os.environ["HMAC_SECRET_KEY"] = "my_secret_key"

    try:
        app = create_app()
        client = TestClient(app)

        timestamp_str = str(int(time.time()))
        message = timestamp_str.encode("utf-8") + b""
        sig = hmac.new(b"my_secret_key", message, hashlib.sha256).hexdigest()

        resp = client.get('/api/v1/core/', headers={
            "x-signature": sig,
            "x-timestamp": timestamp_str
        })
        assert resp.status_code == 200

        resp_fail = client.get('/api/v1/core/', headers={
            "x-signature": "wrong",
            "x-timestamp": timestamp_str
        })
        assert resp_fail.status_code == 401
    finally:
        if original_deploy is not None:
            os.environ["SPENDOO_DEPLOY"] = original_deploy
        else:
            del os.environ["SPENDOO_DEPLOY"]
        if original_secret is not None:
            os.environ["HMAC_SECRET_KEY"] = original_secret
        else:
            del os.environ["HMAC_SECRET_KEY"]


def test_hmac_signing_development_bypass():
    import os
    from fastapi.testclient import TestClient
    from app import create_app

    original_deploy = os.environ.get("SPENDOO_DEPLOY")
    os.environ["SPENDOO_DEPLOY"] = "false"

    try:
        app = create_app()
        client = TestClient(app)

        resp = client.get('/api/v1/core/')
        assert resp.status_code == 200
    finally:
        if original_deploy is not None:
            os.environ["SPENDOO_DEPLOY"] = original_deploy
        else:
            del os.environ["SPENDOO_DEPLOY"]

