from fastapi.testclient import TestClient

from main import app


def test_integration_auth_accepts_bearer_or_proxy_safe_header(monkeypatch):
    monkeypatch.setenv("GEO_ENGINE_HANDOFF_TOKEN", "test-secret")
    client = TestClient(app)
    path = "/api/v1/integration/research-results/not-present"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer test-secret"}).status_code == 404
    assert client.get(path, headers={"X-GEO-Engine-Handoff-Token": "test-secret"}).status_code == 404


def test_integration_auth_does_not_accept_malformed_proxy_header(monkeypatch):
    monkeypatch.setenv("GEO_ENGINE_HANDOFF_TOKEN", "test-secret")
    client = TestClient(app)
    response = client.get(
        "/api/v1/integration/research-results/not-present",
        headers={"X-GEO-Engine-Handoff-Token": "Bearer test-secret"},
    )
    assert response.status_code == 404
