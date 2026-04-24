from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from models.payment import Base


class IdempotencyKey(Base):
    """
    Stores the response body for a given (endpoint, Idempotency-Key) so a retry
    with the same key returns the identical response — even if the duplicate
    request arrives while the original is still processing, we never charge twice.
    """
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(120), nullable=False, unique=True, index=True)
    endpoint = Column(String(120), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
