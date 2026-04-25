import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from events.payment_events import publisher
from models.payment import PaymentCreateRequest, PaymentORM, PaymentResponse
from models.payment_status import PaymentMethod, PaymentStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger("payments.service")

SUPPORTED_METHODS = {m.value for m in PaymentMethod}
PROCESSING_DELAY_SECONDS = 2


class PaymentNotFoundError(Exception):
    pass


def _validate_request(req: PaymentCreateRequest) -> None:
    if req.amount <= Decimal(0):
        raise ValueError("amount must be positive")
    if req.method.value not in SUPPORTED_METHODS:
        raise ValueError(f"unsupported payment method: {req.method}")


def _simulate_processing(amount: Decimal, method: str) -> PaymentStatus:
    """
    Deterministic simulation for tests/portfolio:
      - boletos always confirm
      - amounts >= 100000 fail (fraud check)
      - everything else confirms
    """
    if amount >= Decimal("100000"):
        return PaymentStatus.FAILED
    _ = method  # placeholder for real gateway hook
    return PaymentStatus.CONFIRMED


async def create_payment(session: AsyncSession, req: PaymentCreateRequest) -> PaymentResponse:
    _validate_request(req)

    row = PaymentORM(
        order_id=req.order_id,
        amount=req.amount,
        method=req.method.value,
        status=PaymentStatus.PROCESSING.value,
    )
    session.add(row)
    await session.flush()

    await asyncio.sleep(PROCESSING_DELAY_SECONDS)
    final_status = _simulate_processing(req.amount, req.method.value)

    row.status = final_status.value
    row.processed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(row)

    topic = "payment-confirmed" if final_status == PaymentStatus.CONFIRMED else "payment-failed"
    await publisher.publish(topic, str(row.order_id), {
        "payment_id": row.id,
        "order_id": row.order_id,
        "amount": str(row.amount),
        "method": row.method,
        "status": row.status,
    })
    log.info("payment %s finished with status=%s", row.id, row.status)
    return PaymentResponse.from_orm_row(row)


async def get_payment(session: AsyncSession, payment_id: int) -> PaymentResponse:
    row = await session.get(PaymentORM, payment_id)
    if row is None:
        raise PaymentNotFoundError(f"payment {payment_id} not found")
    return PaymentResponse.from_orm_row(row)


async def list_by_order(session: AsyncSession, order_id: int) -> list[PaymentResponse]:
    result = await session.execute(
        select(PaymentORM).where(PaymentORM.order_id == order_id).order_by(PaymentORM.id.desc())
    )
    return [PaymentResponse.from_orm_row(r) for r in result.scalars()]
