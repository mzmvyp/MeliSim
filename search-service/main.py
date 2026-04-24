import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from consumers.product_consumer import run_consumer
from routes.search_routes import router as search_router
from services.search_service import service

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)

_stop_event: asyncio.Event
_consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _stop_event, _consumer_task
    await service.ensure_index()
    _stop_event = asyncio.Event()
    _consumer_task = asyncio.create_task(run_consumer(_stop_event))
    yield
    _stop_event.set()
    if _consumer_task is not None:
        try:
            await asyncio.wait_for(_consumer_task, timeout=5)
        except asyncio.TimeoutError:
            _consumer_task.cancel()
    await service.close()


app = FastAPI(title="MeliSim Search Service", version="1.0.0", lifespan=lifespan)
app.include_router(search_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "search-service"}
