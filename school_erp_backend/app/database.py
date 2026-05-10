"""Async SQLAlchemy engine, session, and tenant-aware base model."""

from typing import AsyncGenerator

from sqlalchemy import Column, DateTime, Index, Integer, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _engine_kwargs() -> dict:
    if settings.DATABASE_URL.startswith("sqlite"):
        # SQLite (dev) does not support connection pooling tuning the same way.
        return {"echo": settings.DEBUG}
    return {
        "echo": settings.DEBUG,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_pre_ping": True,
    }


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Root declarative base for all models."""


class TimestampMixin:
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class TenantBase(Base, TimestampMixin):
    """Abstract base for every tenant-scoped table.

    Every concrete subclass automatically gets a tenant_id column + index, so
    the multi-tenant filter is impossible to forget at model-definition time.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def tenant_id(cls):
        from sqlalchemy import ForeignKey

        return Column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def __table_args__(cls):
        return (
            Index(f"ix_{cls.__tablename__}_tenant", "tenant_id"),
            {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
