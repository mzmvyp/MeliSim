import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import NotificationORM, NotificationResponse
from services import email_service, push_service

log = logging.getLogger("notifications.service")


async def record(
    session: AsyncSession,
    user_id: int,
    channel: str,
    event_type: str,
    subject: str | None,
    body: str | None,
) -> NotificationORM:
    row = NotificationORM(
        user_id=user_id,
        channel=channel,
        event_type=event_type,
        subject=subject,
        body=body,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def history(session: AsyncSession, user_id: int) -> list[NotificationResponse]:
    result = await session.execute(
        select(NotificationORM)
        .where(NotificationORM.user_id == user_id)
        .order_by(NotificationORM.id.desc())
    )
    return [NotificationResponse.from_orm_row(r) for r in result.scalars()]


async def dispatch_order_created(session: AsyncSession, payload: dict) -> None:
    user_id = int(payload.get("buyerId") or payload.get("buyer_id") or 0)
    order_id = payload.get("id") or payload.get("order_id")
    body = email_service.render(
        "order_confirmed.html",
        order_id=order_id,
        product_id=payload.get("productId") or payload.get("product_id"),
        quantity=payload.get("quantity"),
        total_amount=payload.get("totalAmount") or payload.get("total_amount"),
        status=payload.get("status", "CREATED"),
    )
    subject = f"Order #{order_id} received"
    email_service.send_email(user_id, subject, body)
    await record(session, user_id, "email", "order-created", subject, body)


async def dispatch_payment_confirmed(session: AsyncSession, payload: dict) -> None:
    user_id = int(payload.get("buyer_id") or 0)
    order_id = payload.get("order_id")
    body = email_service.render(
        "payment_confirmed.html",
        order_id=order_id,
        amount=payload.get("amount"),
        method=payload.get("method"),
    )
    subject = f"Payment confirmed for order #{order_id}"
    email_service.send_email(user_id, subject, body)
    push_service.send_push(user_id, subject, f"Order #{order_id} is now PAID")
    await record(session, user_id, "email", "payment-confirmed", subject, body)


async def dispatch_payment_failed(session: AsyncSession, payload: dict) -> None:
    user_id = int(payload.get("buyer_id") or 0)
    order_id = payload.get("order_id")
    body = email_service.render(
        "payment_failed.html",
        order_id=order_id,
        amount=payload.get("amount"),
        method=payload.get("method"),
    )
    subject = f"Payment failed for order #{order_id}"
    email_service.send_email(user_id, subject, body)
    await record(session, user_id, "email", "payment-failed", subject, body)


async def dispatch_stock_alert(session: AsyncSession, payload: dict) -> None:
    seller_id = int(payload.get("seller_id") or 0)
    body = email_service.render(
        "stock_alert.html",
        product_id=payload.get("product_id"),
        title=payload.get("title", "Your product"),
        stock=payload.get("stock", 0),
    )
    subject = f"Low stock for product #{payload.get('product_id')}"
    email_service.send_email(seller_id, subject, body)
    await record(session, seller_id, "email", "stock-alert", subject, body)
