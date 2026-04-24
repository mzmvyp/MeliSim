import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from middleware.auth import AuthMiddleware
from middleware.cors import setup_cors
from middleware.rate_limiter import RateLimiterMiddleware
from routes.router import router as gateway_router

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
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
app.add_middleware(
    RateLimiterMiddleware,
    max_requests=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100")),
    window_seconds=60,
)
app.add_middleware(AuthMiddleware)

app.include_router(gateway_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.exception_handler(httpx.HTTPError)
async def httpx_error_handler(request: Request, exc: httpx.HTTPError):
    logger.error(f"upstream error: {exc}")
    return JSONResponse(status_code=502, content={"error": "Bad Gateway", "detail": str(exc)})
