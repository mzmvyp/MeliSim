import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.idempotency import IdempotencyKey


def fingerprint(body: dict) -> str:
    """SHA-256 over the canonical JSON body — same input, same key."""
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class IdempotencyConflict(Exception):
    """Same key reused with a DIFFERENT body — 422."""


async def get_stored(session: AsyncSession, key: str) -> IdempotencyKey | None:
    result = await session.execute(
        select(IdempotencyKey).where(IdempotencyKey.idempotency_key == key)
    )
    return result.scalars().first()


async def store(
    session: AsyncSession,
    key: str,
    endpoint: str,
    body_fingerprint: str,
    status: int,
    response_body: str,
) -> None:
    row = IdempotencyKey(
        idempotency_key=key,
        endpoint=endpoint,
        request_fingerprint=body_fingerprint,
        response_status=status,
        response_body=response_body,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        # Another request already stored it — race is fine; caller re-reads.
        await session.rollback()
