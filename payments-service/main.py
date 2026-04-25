import logging
from contextlib import asynccontextmanager

from db import engine
from events.payment_events import publisher
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from models.idempotency import IdempotencyKey  # noqa: F401 — register on Base.metadata
from models.payment import Base
from observability import install as install_observability
from routes.payment_routes import router as payments_router
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await publisher.start()
    yield
    await publisher.stop()
    await engine.dispose()


app = FastAPI(title="MeliSim Payments Service", version="1.0.0", lifespan=lifespan)
install_observability(app)
app.include_router(payments_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "payments-service"}


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not-ready", "db": str(e)})
