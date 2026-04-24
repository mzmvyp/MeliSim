from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import PaymentCreateRequest, PaymentResponse
from services.payment_service import (
    PaymentNotFoundError,
    create_payment,
    get_payment,
    list_by_order,
)

router = APIRouter(prefix="/payments", tags=["payments"])


def _get_session_dep():
    # Imported lazily in main to avoid circular imports
    from main import get_session
    return get_session


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create(req: PaymentCreateRequest, session: AsyncSession = Depends(_get_session_dep())):
    try:
        return await create_payment(session, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get(payment_id: int, session: AsyncSession = Depends(_get_session_dep())):
    try:
        return await get_payment(session, payment_id)
    except PaymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/order/{order_id}", response_model=list[PaymentResponse])
async def by_order(order_id: int, session: AsyncSession = Depends(_get_session_dep())):
    return await list_by_order(session, order_id)
