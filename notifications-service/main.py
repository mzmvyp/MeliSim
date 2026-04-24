import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from consumers.notification_consumer import run_consumer
from models.notification import Base, NotificationResponse
from observability import install as install_observability
from services.notification_service import history

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


_stop_event: asyncio.Event
_consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _stop_event, _consumer_task
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _stop_event = asyncio.Event()
    _consumer_task = asyncio.create_task(run_consumer(SessionLocal, _stop_event))
    yield
    _stop_event.set()
    if _consumer_task is not None:
        try:
            await asyncio.wait_for(_consumer_task, timeout=5)
        except asyncio.TimeoutError:
            _consumer_task.cancel()
    await engine.dispose()


app = FastAPI(title="MeliSim Notifications Service", version="1.0.0", lifespan=lifespan)
install_observability(app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notifications-service"}


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    from sqlalchemy import text
    from fastapi.responses import JSONResponse
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not-ready", "detail": str(e)})


@app.get("/notifications/user/{user_id}", response_model=list[NotificationResponse])
async def by_user(user_id: int, session: AsyncSession = Depends(get_session)):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="invalid user id")
    return await history(session, user_id)
