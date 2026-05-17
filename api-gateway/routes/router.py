import asyncio
import math
import os
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter()

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

UPSTREAMS = {
    "users": os.getenv("USERS_SERVICE_URL", "http://users-service:8001"),
    "products": os.getenv("PRODUCTS_SERVICE_URL", "http://products-service:8002"),
    "orders": os.getenv("ORDERS_SERVICE_URL", "http://orders-service:8003"),
    "payments": os.getenv("PAYMENTS_SERVICE_URL", "http://payments-service:8004"),
    "notifications": os.getenv("NOTIFICATIONS_SERVICE_URL", "http://notifications-service:8005"),
    "search": os.getenv("SEARCH_SERVICE_URL", "http://search-service:8006"),
}

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


async def _proxy(request: Request, upstream: str, upstream_path: str) -> Response:
    client: httpx.AsyncClient = request.app.state.http_client
    url = f"{upstream.rstrip('/')}/{upstream_path.lstrip('/')}"
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    rid = getattr(request.state, "request_id", None)
    if rid:
        headers["x-request-id"] = rid

    upstream_resp = await client.request(
        method=request.method,
        url=url,
        params=dict(request.query_params),
        content=body,
        headers=headers,
    )
    resp_headers = {k: v for k, v in upstream_resp.headers.items() if k.lower() not in HOP_BY_HOP}
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )


# ---- Auth / Users ----
@router.api_route("/auth/register", methods=["POST"])
async def auth_register(request: Request):
    return await _proxy(request, UPSTREAMS["users"], "/users/register")


@router.api_route("/auth/login", methods=["POST"])
async def auth_login(request: Request):
    return await _proxy(request, UPSTREAMS["users"], "/users/login")


@router.api_route("/users/{user_id}", methods=["GET", "PUT", "DELETE"])
async def users_by_id(user_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["users"], f"/users/{user_id}")


# ---- Products ----
@router.api_route("/products", methods=["GET", "POST"])
async def products_root(request: Request):
    return await _proxy(request, UPSTREAMS["products"], "/products")


@router.api_route("/products/search", methods=["GET"])
async def products_search(request: Request):
    # search goes to search-service, not products-service
    return await _proxy(request, UPSTREAMS["search"], "/search")


@router.api_route("/products/suggestions", methods=["GET"])
async def products_suggestions(request: Request):
    return await _proxy(request, UPSTREAMS["search"], "/search/suggestions")


@router.api_route("/products/{product_id}", methods=["GET", "PUT", "DELETE"])
async def products_by_id(product_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["products"], f"/products/{product_id}")


@router.api_route("/products/{product_id}/stock", methods=["PATCH"])
async def products_stock(product_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["products"], f"/products/{product_id}/stock")


# ---- Orders ----
@router.api_route("/orders", methods=["POST"])
async def orders_create(request: Request):
    return await _proxy(request, UPSTREAMS["orders"], "/orders")


@router.api_route("/orders/{order_id}", methods=["GET"])
async def orders_get(order_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["orders"], f"/orders/{order_id}")


@router.api_route("/orders/{order_id}/status", methods=["PATCH"])
async def orders_status(order_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["orders"], f"/orders/{order_id}/status")


@router.api_route("/orders/user/{user_id}", methods=["GET"])
async def orders_by_user(user_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["orders"], f"/orders/user/{user_id}")


# ---- Payments ----
@router.api_route("/payments", methods=["POST"])
async def payments_create(request: Request):
    return await _proxy(request, UPSTREAMS["payments"], "/payments")


@router.api_route("/payments/{payment_id}", methods=["GET"])
async def payments_get(payment_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["payments"], f"/payments/{payment_id}")


@router.api_route("/payments/order/{order_id}", methods=["GET"])
async def payments_by_order(order_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["payments"], f"/payments/order/{order_id}")


# ---- Notifications ----
@router.api_route("/notifications/user/{user_id}", methods=["GET"])
async def notifications_by_user(user_id: str, request: Request):
    return await _proxy(request, UPSTREAMS["notifications"], f"/notifications/user/{user_id}")


# ---- Admin: aggregated health check ----
# The browser cannot ping internal services directly because Spring/chi don't
# send CORS headers — but the gateway lives in the same docker network, so it
# pings each service and returns one consolidated response (CORS-allowed by
# the gateway itself).
_HEALTH_TARGETS = [
    {"name": "api-gateway",         "lang": "Python", "port": 8000, "url": "http://api-gateway:8000/health"},
    {"name": "users-service",       "lang": "Java",   "port": 8001, "url": f"{UPSTREAMS['users']}/actuator/health"},
    {"name": "products-service",    "lang": "Go",     "port": 8002, "url": f"{UPSTREAMS['products']}/health"},
    {"name": "orders-service",      "lang": "Kotlin", "port": 8003, "url": f"{UPSTREAMS['orders']}/actuator/health"},
    {"name": "payments-service",    "lang": "Python", "port": 8004, "url": f"{UPSTREAMS['payments']}/health"},
    {"name": "notifications-service","lang":"Python","port": 8005, "url": f"{UPSTREAMS['notifications']}/health"},
    {"name": "search-service",      "lang": "Python", "port": 8006, "url": f"{UPSTREAMS['search']}/health"},
    {"name": "stock-monitor",       "lang": "Go",     "port": 8099, "url": "http://stock-monitor:8099/health"},
]


def _require_admin(request: Request) -> None:
    user = getattr(request.state, "user", None) or {}
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")


async def _ping_one(client: httpx.AsyncClient, target: dict) -> dict:
    start = time.perf_counter()
    try:
        r = await client.get(target["url"], timeout=2.0)
        elapsed = int((time.perf_counter() - start) * 1000)
        return {**target, "up": r.is_success, "status": r.status_code, "elapsedMs": elapsed}
    except Exception as e:
        elapsed = int((time.perf_counter() - start) * 1000)
        return {**target, "up": False, "status": 0, "elapsedMs": elapsed, "error": type(e).__name__}


def _sanitize_health_row(row: dict) -> dict:
    """Strip internal docker URLs from the JSON seen by browsers."""
    return {k: v for k, v in row.items() if k != "url"}


def _prom_parse_scalar(payload: dict[str, Any]) -> Optional[float]:
    try:
        results = payload.get("data", {}).get("result") or []
        if not results:
            return None
        raw = results[0].get("value")
        if not raw or len(raw) < 2:
            return None
        s = str(raw[1]).lower()
        if s in ("nan", "+inf", "-inf", "inf"):
            return None
        v = float(raw[1])
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


async def _prom_scalar(client: httpx.AsyncClient, query: str) -> Optional[float]:
    try:
        r = await client.get(
            f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query",
            params={"query": query},
            timeout=6.0,
        )
        if not r.is_success:
            return None
        return _prom_parse_scalar(r.json())
    except Exception:
        return None


async def _prom_instant_rows(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    try:
        r = await client.get(
            f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query",
            params={"query": query},
            timeout=8.0,
        )
        if not r.is_success:
            return []
        rows = r.json().get("data", {}).get("result") or []
        out: list[dict[str, Any]] = []
        for row in rows:
            metric = row.get("metric") or {}
            val = row.get("value")
            if not val or len(val) < 2:
                continue
            try:
                v = float(val[1])
                if math.isnan(v) or math.isinf(v):
                    continue
                out.append({"metric": metric, "value": v})
            except (TypeError, ValueError):
                continue
        return out
    except Exception:
        return []


def _float_by_job(rows: list[dict[str, Any]]) -> dict[str, float]:
    m: dict[str, float] = {}
    for row in rows:
        job = row["metric"].get("job")
        if not job:
            continue
        m[job] = float(row["value"])
    return m


def _merge_rps_maps(*maps: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for mp in maps:
        for job, v in mp.items():
            out[job] = out.get(job, 0.0) + v
    return out


def _merge_p95_maps(py_sec: dict[str, float], spring_sec: dict[str, float]) -> dict[str, float]:
    """One p95 per job — Python/Go histogram vs Spring; jobs are disjoint in practice."""
    keys = set(py_sec) | set(spring_sec)
    merged: dict[str, float] = {}
    for job in keys:
        if job in py_sec:
            merged[job] = py_sec[job]
        elif job in spring_sec:
            merged[job] = spring_sec[job]
    return merged


@router.get("/admin/service-metrics")
async def admin_service_metrics(request: Request):
    """Per-job RPS and HTTP p95 from Prometheus (job matches scrape config names)."""
    _require_admin(request)
    client: httpx.AsyncClient = request.app.state.http_client

    q_rps_py = "sum by (job)(rate(http_requests_total[2m]))"
    q_rps_sp = "sum by (job)(rate(http_server_requests_seconds_count[2m]))"
    q_p95_py = (
        "histogram_quantile(0.95, sum by (le, job) ("
        "rate(http_request_duration_seconds_bucket[5m])))"
    )
    q_p95_sp = (
        "histogram_quantile(0.95, sum by (le, job) ("
        "rate(http_server_requests_seconds_bucket[5m])))"
    )

    r_py, r_sp, p_py, p_sp = await asyncio.gather(
        _prom_instant_rows(client, q_rps_py),
        _prom_instant_rows(client, q_rps_sp),
        _prom_instant_rows(client, q_p95_py),
        _prom_instant_rows(client, q_p95_sp),
    )

    rps = _merge_rps_maps(_float_by_job(r_py), _float_by_job(r_sp))
    p95_sec = _merge_p95_maps(_float_by_job(p_py), _float_by_job(p_sp))

    services_out: list[dict[str, Any]] = []
    for t in _HEALTH_TARGETS:
        name = t["name"]
        rps_v = rps.get(name)
        p95_ms: Optional[float] = None
        if name in p95_sec:
            p95_ms = p95_sec[name] * 1000.0
        services_out.append(
            {
                "name": name,
                "requests_per_second": rps_v,
                "latency_p95_ms": p95_ms,
            }
        )

    return {
        "checked_at": time.time(),
        "prometheus_ok": bool(rps or p95_sec),
        "services": services_out,
    }


@router.get("/admin/dashboard-kpis")
async def admin_dashboard_kpis(request: Request):
    """Aggregated KPIs from Prometheus + outbox summary (orders-service)."""
    _require_admin(request)
    client: httpx.AsyncClient = request.app.state.http_client

    q_rps = (
        "sum(rate(http_requests_total[2m])) + "
        "sum(rate(http_server_requests_seconds_count[2m]))"
    )
    q_err = (
        "("
        'sum(rate(http_requests_total{status=~"5.."}[5m])) + '
        'sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))'
        ") / clamp_min("
        "sum(rate(http_requests_total[5m])) + "
        "sum(rate(http_server_requests_seconds_count[5m])), "
        "0.001)"
    )
    q_kafka = "sum(rate(melisim_events_published_total[2m]))"

    rps, err_ratio, kafka_rps = await asyncio.gather(
        _prom_scalar(client, q_rps),
        _prom_scalar(client, q_err),
        _prom_scalar(client, q_kafka),
    )

    outbox_pending: Optional[int] = None
    outbox_hint: Optional[str] = None
    try:
        ro = await client.get(f"{UPSTREAMS['orders']}/admin/outbox/summary", timeout=6.0)
        if ro.is_success:
            body = ro.json()
            if body.get("pending") is not None:
                outbox_pending = int(body["pending"])
            outbox_hint = "orders-service / MySQL"
    except Exception:
        pass

    rpm = (rps * 60.0) if rps is not None else None

    return {
        "requests_per_second": rps,
        "requests_per_minute": rpm,
        "error_rate": err_ratio,
        "kafka_events_per_second": kafka_rps,
        "kafka_topic_count": 6,
        "outbox_pending": outbox_pending,
        "outbox_source_hint": outbox_hint,
        "prometheus_ok": any(x is not None for x in (rps, err_ratio, kafka_rps)),
    }


@router.get("/admin/services-health")
async def services_health(request: Request):
    _require_admin(request)
    client: httpx.AsyncClient = request.app.state.http_client
    results = await asyncio.gather(*[_ping_one(client, t) for t in _HEALTH_TARGETS])
    up = sum(1 for r in results if r["up"])
    return {
        "checked_at": time.time(),
        "summary": {"total": len(results), "up": up, "down": len(results) - up},
        "services": [_sanitize_health_row(r) for r in results],
    }


@router.get("/admin/outbox/summary")
async def admin_outbox_summary(request: Request):
    _require_admin(request)
    return await _proxy(request, UPSTREAMS["orders"], "/admin/outbox/summary")


# DLQ topic catalogue — kept in sync with infra/kafka/topics.sh (no Kafka REST in stack).
_DLQ_TOPICS = [
    {"name": "order-created.dlq", "partitions": 1, "retentionDays": 30},
    {"name": "payment-confirmed.dlq", "partitions": 1, "retentionDays": 30},
    {"name": "payment-failed.dlq", "partitions": 1, "retentionDays": 30},
    {"name": "stock-alert.dlq", "partitions": 1, "retentionDays": 30},
    {"name": "product-created.dlq", "partitions": 1, "retentionDays": 30},
    {"name": "stock-updates.dlq", "partitions": 1, "retentionDays": 30},
]


@router.get("/admin/dlq/topics")
async def admin_dlq_topics(request: Request):
    _require_admin(request)
    return {
        "topics": _DLQ_TOPICS,
        "cliHint": "docker exec -it melisim-kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic <name> --from-beginning",
    }
