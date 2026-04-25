from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NotificationORM(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    channel = Column(String(30), nullable=False)
    event_type = Column(String(60), nullable=False)
    subject = Column(String(200), nullable=True)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    channel: str
    event_type: str
    subject: str | None = None
    body: str | None = None
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: NotificationORM) -> "NotificationResponse":
        return cls(
            id=row.id,
            user_id=row.user_id,
            channel=row.channel,
            event_type=row.event_type,
            subject=row.subject,
            body=row.body,
            created_at=row.created_at,
        )
