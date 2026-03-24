from __future__ import annotations

import app.main as main_module


def test_health_backward_compatible_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_live_endpoint(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alive"
    assert payload["service"] == "backend"
    assert payload["version"]


def test_health_ready_endpoint_success(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] == "ok"


def test_health_ready_endpoint_failure(client, monkeypatch):
    def fake_readiness_payload(*, session_factory=None):
        return (
            {
                "status": "not_ready",
                "service": "backend",
                "version": "0.1.0",
                "checks": {"database": "error"},
                "details": {"database": "ConnectionError"},
            },
            False,
        )

    monkeypatch.setattr(main_module, "build_readiness_payload", fake_readiness_payload)

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["database"] == "error"


def test_health_ready_endpoint_checks_cos_storage_runtime(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cos")
    monkeypatch.setattr(settings, "TENCENT_COS_SECRET_ID", "")
    monkeypatch.setattr(settings, "TENCENT_COS_SECRET_KEY", "")
    monkeypatch.setattr(settings, "TENCENT_COS_BUCKET", "")
    monkeypatch.setattr(settings, "TENCENT_COS_REGION", "")

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["storage"] == "error"
