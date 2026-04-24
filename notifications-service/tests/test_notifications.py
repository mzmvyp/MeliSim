import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.notification import Base
from services import notification_service


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_order_created_records_and_sends(session):
    with patch("services.notification_service.email_service.send_email") as send:
        await notification_service.dispatch_order_created(session, {
            "id": 1, "buyerId": 42, "productId": 7, "quantity": 2,
            "totalAmount": "100.00", "status": "CREATED",
        })
    send.assert_called_once()
    rows = await notification_service.history(session, 42)
    assert len(rows) == 1
    assert rows[0].event_type == "order-created"


@pytest.mark.asyncio
async def test_payment_confirmed_dispatches_email_and_push(session):
    with patch("services.notification_service.email_service.send_email") as email, \
         patch("services.notification_service.push_service.send_push") as push:
        await notification_service.dispatch_payment_confirmed(session, {
            "order_id": 1, "buyer_id": 5, "amount": "100.00", "method": "pix",
        })
    email.assert_called_once()
    push.assert_called_once()


@pytest.mark.asyncio
async def test_stock_alert_targets_seller(session):
    with patch("services.notification_service.email_service.send_email") as email:
        await notification_service.dispatch_stock_alert(session, {
            "seller_id": 9, "product_id": 7, "title": "Book", "stock": 2,
        })
    email.assert_called_once()
    rows = await notification_service.history(session, 9)
    assert rows[0].event_type == "stock-alert"


@pytest.mark.asyncio
async def test_history_empty_for_unknown_user(session):
    rows = await notification_service.history(session, 999)
    assert rows == []
