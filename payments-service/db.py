import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://melisim:melisim123@localhost:5432/melisim",
)

# Pool tuning. asyncpg under the hood:
#   pool_size:         baseline open connections kept warm
#   max_overflow:      headroom over pool_size before requests start to queue
#   pool_pre_ping:     cheap SELECT 1 before checkout — survives DB restarts/firewall idle-kills
#   pool_recycle:      recycle connections every 30 min (under most idle-timeout policies)
#   pool_timeout:      how long a request waits for a connection before failing fast
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=10,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
