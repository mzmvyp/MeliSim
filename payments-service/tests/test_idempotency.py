import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.idempotency import IdempotencyKey  # noqa: F401 — register table
from models.payment import Base
from services.idempotency_service import fingerprint, get_stored, store


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


def test_fingerprint_is_stable_for_same_body():
    a = {"order_id": 1, "amount": "10.00", "method": "pix"}
    b = {"amount": "10.00", "method": "pix", "order_id": 1}
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_changes_when_body_changes():
    a = {"order_id": 1, "amount": "10.00"}
    b = {"order_id": 2, "amount": "10.00"}
    assert fingerprint(a) != fingerprint(b)


@pytest.mark.asyncio
async def test_store_and_retrieve_roundtrip(session):
    key = "test-key-abc"
    await store(session, key, "POST /payments", "fp1", 201, '{"ok":true}')
    got = await get_stored(session, key)
    assert got is not None
    assert got.response_status == 201
    assert got.response_body == '{"ok":true}'
    assert got.request_fingerprint == "fp1"


@pytest.mark.asyncio
async def test_retrieve_missing_returns_none(session):
    assert await get_stored(session, "not-there") is None
