import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from middleware.auth import AuthMiddleware
from middleware.correlation import CorrelationIdMiddleware, RequestIdLogFilter
from middleware.cors import setup_cors
from middleware.metrics import PrometheusMiddleware, metrics_endpoint
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.rate_limiter_redis import RedisRateLimiterMiddleware
from observability import setup_tracing
from routes.router import router as gateway_router

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","request_id":"%(request_id)s","msg":"%(message)s"}',
)
logging.getLogger().addFilter(RequestIdLogFilter())
logger = logging.getLogger("api-gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("api-gateway started")
    yield
    await app.state.http_client.aclose()
    logger.info("api-gateway stopped")


app = FastAPI(title="MeliSim API Gateway", version="1.0.0", lifespan=lifespan)

setup_cors(app)
setup_tracing(app)
app.add_middleware(PrometheusMiddleware)

# Prefer Redis-backed rate limiter when REDIS_URL is set (multi-instance safe).
# Falls back to the in-memory sliding window otherwise (still useful for dev).
_redis_url = os.getenv("REDIS_URL")
_rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
if _redis_url:
    app.add_middleware(
        RedisRateLimiterMiddleware,
        redis_url=_redis_url,
        max_requests=_rate_limit,
        window_seconds=60,
    )
else:
    app.add_middleware(
        RateLimiterMiddleware,
        max_requests=_rate_limit,
        window_seconds=60,
    )
app.add_middleware(AuthMiddleware)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(gateway_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    try:
        r = await app.state.http_client.get(
            f"{os.getenv('USERS_SERVICE_URL', 'http://users-service:8001')}/users/health",
            timeout=2,
        )
        r.raise_for_status()
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not-ready", "detail": str(e)})


@app.get("/metrics")
async def metrics():
    return metrics_endpoint()


@app.exception_handler(httpx.HTTPError)
async def httpx_error_handler(request: Request, exc: httpx.HTTPError):
    logger.error(f"upstream error: {exc}")
    return JSONResponse(status_code=502, content={"error": "Bad Gateway", "detail": str(exc)})
