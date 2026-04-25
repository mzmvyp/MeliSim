import json

from db import get_session
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from models.payment import PaymentCreateRequest, PaymentResponse
from services.idempotency_service import (
    IdempotencyConflict,
    fingerprint,
    get_stored,
    store,
)
from services.payment_service import (
    PaymentNotFoundError,
    create_payment,
    get_payment,
    list_by_order,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create(
    req: PaymentCreateRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
):
    body = req.model_dump(mode="json")
    body_fp = fingerprint(body)

    # ---- Idempotency: replay a prior response when the same key shows up ----
    if idempotency_key:
        prior = await get_stored(session, idempotency_key)
        if prior is not None:
            if prior.request_fingerprint != body_fp:
                raise HTTPException(
                    status_code=422,
                    detail="Idempotency-Key reused with a different request body",
                )
            response.headers["Idempotent-Replayed"] = "true"
            return json.loads(prior.response_body)

    try:
        payment = await create_payment(session, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except IdempotencyConflict as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    if idempotency_key:
        await store(
            session=session,
            key=idempotency_key,
            endpoint="POST /payments",
            body_fingerprint=body_fp,
            status=201,
            response_body=payment.model_dump_json(),
        )

    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get(payment_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await get_payment(session, payment_id)
    except PaymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/order/{order_id}", response_model=list[PaymentResponse])
async def by_order(order_id: int, session: AsyncSession = Depends(get_session)):
    return await list_by_order(session, order_id)
