import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter()

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
