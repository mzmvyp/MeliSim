import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from events.payment_events import publisher
from models.payment import Base
from routes.payment_routes import router as payments_router

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://melisim:melisim123@localhost:5432/melisim",
)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


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
