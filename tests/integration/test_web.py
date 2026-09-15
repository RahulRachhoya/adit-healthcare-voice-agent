import re

import pytest
from fastapi.testclient import TestClient

from adit_voice_agent.web.app import create_app
from tests.conftest import TEST_PASSWORD


@pytest.fixture
def client(settings, sessions, gateway, fakes):
    with TestClient(create_app(settings, sessions, gateway, fakes.adapter, fakes.recording)) as client:
        yield client


def token(client):
    response = client.get("/login")
    return re.search(r'name="csrf-token" content="([^"]+)"', response.text).group(1)


def sign_in(client):
    csrf = token(client)
    response = client.post("/login", data={"username": "operator", "password": TEST_PASSWORD, "csrf": csrf})
    assert response.status_code == 200
    return re.search(r'name="csrf-token" content="([^"]+)"', response.text).group(1)


@pytest.mark.parametrize("path", ["/api/calls", "/api/readiness", "/api/calls/missing", "/api/calls/missing/recording"])
def test_private_endpoints_require_login(client, path):
    assert client.get(path).status_code == 401


def test_login_form_and_session_flags(client):
    response = client.get("/login")
    assert client.get("/").url.path == "/login"
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=strict" in response.headers["set-cookie"].lower()
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_login_and_mutations_require_csrf(client, patient):
    assert client.post("/login", data={"username": "operator", "password": TEST_PASSWORD}).status_code == 403
    csrf = sign_in(client)
    body = patient.model_dump(mode="json")
    assert client.post("/api/calls", json=body, headers={"Idempotency-Key": "key"}).status_code == 403
    response = client.post("/api/calls", json=body, headers={"Idempotency-Key": "key", "X-CSRF-Token": csrf})
    assert response.status_code == 202
    detail = client.get(f"/calls/{response.json()['id']}")
    assert detail.status_code == 200


def test_readiness_never_returns_credentials(client):
    sign_in(client)
    response = client.get("/api/readiness")
    assert response.status_code == 200
    assert "test-session-secret" not in response.text
    assert "unused" not in response.text
    assert response.json()["live_test_verified"] is False


def test_protected_recording_is_not_available_early(client, active_call):
    sign_in(client)
    assert client.get(f"/api/calls/{active_call}/recording").status_code == 409


def test_logout_invalidates_session(client):
    csrf = sign_in(client)
    client.post("/logout", data={"csrf": csrf})
    assert client.get("/api/calls").status_code == 401


def test_wrong_password_and_login_rate_limit(client):
    csrf = token(client)
    for _ in range(5):
        assert client.post("/login", data={"username": "operator", "password": "wrong", "csrf": csrf}).status_code == 401
    assert client.post("/login", data={"username": "operator", "password": "wrong", "csrf": csrf}).status_code == 429


@pytest.mark.parametrize("method,path", [
    ("GET", "/calls/missing"),
    ("GET", "/api/calls/missing"),
    ("GET", "/api/calls/missing/recording"),
    ("POST", "/api/calls/missing/end"),
])
def test_missing_call_returns_404(client, method, path):
    csrf = sign_in(client)
    response = client.request(method, path, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 404
    assert response.json() == {"detail": "Call not found."}


def test_disabled_call_preserves_service_error(client, patient, settings):
    settings.live_calls_enabled = False
    csrf = sign_in(client)
    response = client.post(
        "/api/calls", json=patient.model_dump(mode="json"),
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "disabled-call"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Live calling is disabled. Complete the setup and trial preflight."


def test_health_endpoint_is_public(client):
    assert client.get("/healthz").json() == {"status": "ok"}
