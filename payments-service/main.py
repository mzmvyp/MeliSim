import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import engine
from events.payment_events import publisher
from models.payment import Base
from routes.payment_routes import router as payments_router

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
app.include_router(payments_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "payments-service"}
