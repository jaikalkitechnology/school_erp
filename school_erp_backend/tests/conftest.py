"""Shared pytest fixtures - sets up an in-memory SQLite DB per test session."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest
import pytest_asyncio

# Use a dedicated dev DB file per test run so we don't fight with the developer's local one.
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False).name
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{_TEST_DB}"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # avoid stomping on dev cache


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_schema():
    """Create every table once per test session via the metadata."""
    # Force a fresh settings instance so the test env vars take effect.
    from app.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.database import Base, engine
    import app.models  # noqa: F401  - register tables

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_plans():
    """Truncate tenant tables and seed plans fresh for the test."""
    from sqlalchemy import delete

    from app.database import AsyncSessionLocal
    from app.models.tenant import (
        Subscription,
        SubscriptionPlan,
        Tenant,
        TenantSettings,
        TenantUsageSnapshot,
    )
    from app.services.seed import seed_plans

    async with AsyncSessionLocal() as session:
        for model in (TenantUsageSnapshot, TenantSettings, Subscription, Tenant, SubscriptionPlan):
            await session.execute(delete(model))
        await session.commit()
        await seed_plans(session)
    yield
