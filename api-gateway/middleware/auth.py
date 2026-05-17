import os
import secrets
from collections.abc import Iterable
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

JWT_SECRET = os.getenv("JWT_SECRET", "melisim-dev-secret")
JWT_ALGORITHM = "HS256"

PUBLIC_PATHS: Iterable[str] = (
    "/health",
    "/health/live",
    "/health/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/products",
    "/api/v1/products/search",
)


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    # GET /api/v1/products/{id} is also public
    if path.startswith("/api/v1/products/") and not path.startswith("/api/v1/products/search"):
        return True
    if path.startswith("/api/v1/products/search"):
        return True
    return False


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _expected_metrics_scrape_token() -> str:
    """
    Machine-to-machine token for Prometheus (or other scrapers) on GET /metrics.
    Prefer METRICS_SCRAPE_TOKEN_FILE so the same file can back Prometheus's
    credentials_file and this service (single secret, no JWT expiry).
    """
    path = os.getenv("METRICS_SCRAPE_TOKEN_FILE", "").strip()
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8").strip()
    return os.getenv("METRICS_SCRAPE_TOKEN", "").strip()


def _metrics_scrape_authorized(request: Request) -> bool:
    expected = _expected_metrics_scrape_token()
    if not expected:
        return False
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return False
    provided = auth.split(" ", 1)[1].strip()
    return secrets.compare_digest(provided, expected)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()

        # CORS preflight must not require JWT (browser sends OPTIONS without Authorization).
        if method == "OPTIONS":
            return await call_next(request)

        if path == "/metrics" and method == "GET" and _metrics_scrape_authorized(request):
            return await call_next(request)

        # Public paths + all GET browse calls on products are unauthenticated
        if _is_public(path) or (method == "GET" and path.startswith("/api/v1/products")):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"error": "Missing bearer token"})

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except JWTError as exc:
            return JSONResponse(status_code=401, content={"error": "Invalid token", "detail": str(exc)})

        request.state.user = payload
        return await call_next(request)
