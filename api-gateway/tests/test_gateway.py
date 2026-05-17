import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "5")

from main import app  # noqa: E402
from middleware.auth import JWT_ALGORITHM, JWT_SECRET  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "api-gateway"


def test_protected_route_rejects_missing_token(client):
    resp = client.post("/api/v1/orders", json={"product_id": 1, "quantity": 1})
    assert resp.status_code == 401
    assert "Missing bearer token" in resp.json()["error"]


def test_protected_route_rejects_invalid_token(client):
    resp = client.post(
        "/api/v1/orders",
        headers={"Authorization": "Bearer not.a.real.jwt"},
        json={"product_id": 1, "quantity": 1},
    )
    assert resp.status_code == 401


def test_rate_limiter_blocks_after_threshold(client):
    # RATE_LIMIT_PER_MINUTE=5 via env → 6th hit on a protected path should 429.
    # Auth fails first (401), but the limiter runs before auth's dispatch returns,
    # so we hit a public-but-not-health path: products GET is public.
    status_codes = []
    for _ in range(12):
        r = client.get("/api/v1/products", headers={"X-Forwarded-For": "9.9.9.9"})
        status_codes.append(r.status_code)
    assert 429 in status_codes


def test_valid_token_passes_auth_layer(client):
    token = jwt.encode({"sub": "42", "role": "BUYER"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # Will 502 since upstream isn't reachable in tests — but it PASSED auth (not 401).
    resp = client.get(
        "/api/v1/orders/123",
        headers={"Authorization": f"Bearer {token}", "X-Forwarded-For": "1.1.1.1"},
    )
    assert resp.status_code != 401


def test_metrics_requires_scrape_token_or_auth(client, monkeypatch):
    monkeypatch.delenv("METRICS_SCRAPE_TOKEN_FILE", raising=False)
    monkeypatch.delenv("METRICS_SCRAPE_TOKEN", raising=False)
    assert client.get("/metrics").status_code == 401

    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "scrape-test-token")
    assert client.get("/metrics").status_code == 401
    assert (
        client.get(
            "/metrics",
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )
    ok = client.get(
        "/metrics",
        headers={"Authorization": "Bearer scrape-test-token"},
    )
    assert ok.status_code == 200
    assert b"# HELP" in ok.content or b"# TYPE" in ok.content


def test_admin_services_health_requires_auth(client):
    assert client.get("/api/v1/admin/services-health").status_code == 401


def test_admin_services_health_forbidden_for_non_admin(client):
    token = jwt.encode({"sub": "1", "role": "BUYER"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get(
        "/api/v1/admin/services-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert "Admin" in r.json().get("detail", "")


def test_admin_services_health_allows_admin_token(client):
    token = jwt.encode({"sub": "99", "role": "ADMIN"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get(
        "/api/v1/admin/services-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Upstreams are not running in unit tests — expect 200 with some services down, or 502.
    assert r.status_code in (200, 502)
    if r.status_code == 200:
        body = r.json()
        assert "services" in body
        assert "summary" in body


def test_admin_outbox_summary_requires_admin(client):
    token = jwt.encode({"sub": "1", "role": "BUYER"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get(
        "/api/v1/admin/outbox/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_admin_dlq_topics_requires_admin(client):
    assert client.get("/api/v1/admin/dlq/topics").status_code == 401
    token = jwt.encode({"sub": "2", "role": "BUYER"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert client.get(
        "/api/v1/admin/dlq/topics",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 403


def test_admin_dlq_topics_returns_catalog(client):
    token = jwt.encode({"sub": "1", "role": "ADMIN"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get(
        "/api/v1/admin/dlq/topics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "topics" in body and len(body["topics"]) >= 6
    assert body["topics"][0]["name"].endswith(".dlq")


def test_admin_dashboard_kpis_requires_admin(client):
    token = jwt.encode({"sub": "1", "role": "BUYER"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert (
        client.get(
            "/api/v1/admin/dashboard-kpis",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 403
    )


def test_admin_dashboard_kpis_returns_payload(client):
    token = jwt.encode({"sub": "1", "role": "ADMIN"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get(
        "/api/v1/admin/dashboard-kpis",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "prometheus_ok" in body
    assert "kafka_topic_count" in body


def test_admin_service_metrics_requires_admin(client):
    token = jwt.encode({"sub": "1", "role": "BUYER"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert (
        client.get(
            "/api/v1/admin/service-metrics",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 403
    )


def test_admin_service_metrics_returns_services(client):
    token = jwt.encode({"sub": "1", "role": "ADMIN"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get(
        "/api/v1/admin/service-metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "services" in body
    assert len(body["services"]) == 8
    names = {s["name"] for s in body["services"]}
    assert "api-gateway" in names
    assert "stock-monitor" in names
