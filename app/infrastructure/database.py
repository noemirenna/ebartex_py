"""
PostgreSQL async connection via SQLAlchemy 2.0 + asyncpg.
Connection pooling (pool_size, max_overflow) to avoid opening a connection per request.
Never log the connection URL (it contains DB_PASS); use settings.DATABASE_URL_MASKED for logs.
"""
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()

# Use DATABASE_URL only for engine creation; do not log it (use settings.DATABASE_URL_MASKED if needed)
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql://") and "asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    _db_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def init_db() -> None:
    """Verify connection on startup. Tables are created via Alembic migrations."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db() -> None:
    """Dispose pool on shutdown."""
    await engine.dispose()


def _session_has_changes(session: AsyncSession) -> bool:
    """True if the session has uncommitted writes (new, dirty, or deleted)."""
    return bool(session.new or session.dirty or session.deleted)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yield async session for request scope. Commits only when there are writes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            if _session_has_changes(session):
                await session.commit()
        except Exception as e:
            await session.rollback()
            if isinstance(e, IntegrityError):
                logger.warning("DB constraint violation (rollback): {} {}", type(e).__name__, e)
            elif isinstance(e, SQLAlchemyError):
                logger.error("DB error (rollback): {} {}", type(e).__name__, e)
            else:
                logger.error("Unexpected error in session (rollback): {} {}", type(e).__name__, e)
            raise
        finally:
            await session.close()
