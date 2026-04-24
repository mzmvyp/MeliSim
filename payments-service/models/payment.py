from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.orm import declarative_base

from .payment_status import PaymentMethod, PaymentStatus

Base = declarative_base()


class PaymentORM(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, default=PaymentStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class PaymentCreateRequest(BaseModel):
    order_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    method: PaymentMethod

    @field_validator("amount")
    @classmethod
    def _amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    method: str
    status: PaymentStatus
    created_at: datetime
    processed_at: Optional[datetime] = None

    @classmethod
    def from_orm_row(cls, row: PaymentORM) -> "PaymentResponse":
        return cls(
            id=row.id,
            order_id=row.order_id,
            amount=row.amount,
            method=row.method,
            status=PaymentStatus(row.status),
            created_at=row.created_at,
            processed_at=row.processed_at,
        )
