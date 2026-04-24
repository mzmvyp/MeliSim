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
