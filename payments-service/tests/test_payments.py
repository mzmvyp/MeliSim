import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.payment import Base, PaymentCreateRequest
from models.payment_status import PaymentMethod, PaymentStatus
from services.payment_service import (
    PROCESSING_DELAY_SECONDS,
    PaymentNotFoundError,
    create_payment,
    get_payment,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture(autouse=True)
def _fast_processing(monkeypatch):
    # Zero-delay for tests.
    monkeypatch.setattr("services.payment_service.PROCESSING_DELAY_SECONDS", 0)


@pytest.mark.asyncio
async def test_create_payment_confirmed(session):
    req = PaymentCreateRequest(order_id=1, amount=Decimal("99.90"), method=PaymentMethod.PIX)
    with patch("services.payment_service.publisher.publish", new_callable=AsyncMock) as pub:
        resp = await create_payment(session, req)
    assert resp.status == PaymentStatus.CONFIRMED
    assert resp.amount == Decimal("99.90")
    pub.assert_awaited_once()
    topic = pub.await_args.args[0]
    assert topic == "payment-confirmed"


@pytest.mark.asyncio
async def test_create_payment_failed_above_threshold(session):
    req = PaymentCreateRequest(order_id=2, amount=Decimal("250000"), method=PaymentMethod.CREDIT_CARD)
    with patch("services.payment_service.publisher.publish", new_callable=AsyncMock) as pub:
        resp = await create_payment(session, req)
    assert resp.status == PaymentStatus.FAILED
    topic = pub.await_args.args[0]
    assert topic == "payment-failed"


@pytest.mark.asyncio
async def test_create_payment_invalid_method_rejected():
    with pytest.raises(ValidationError):
        PaymentCreateRequest(order_id=1, amount=Decimal("10"), method="bitcoin")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_payment_negative_amount_rejected():
    with pytest.raises(ValidationError):
        PaymentCreateRequest(order_id=1, amount=Decimal("-10"), method=PaymentMethod.PIX)


@pytest.mark.asyncio
async def test_get_payment_missing(session):
    with pytest.raises(PaymentNotFoundError):
        await get_payment(session, 999)
