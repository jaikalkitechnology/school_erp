"""Health probes used by load balancers and orchestrators.

- ``/v1/health`` — verbose status with per-dependency strings; always 200.
  Useful for human dashboards / Phase 0 acceptance tests.
- ``/v1/livez`` — process-alive ping; never touches the DB or Redis.
- ``/v1/readyz`` — deep readiness check; returns 503 if DB or Redis is
  unreachable so k8s can pull the pod out of the service mesh.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


async def _check_db() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"down: {exc.__class__.__name__}"


async def _check_redis() -> str:
    try:
        from redis.asyncio import from_url  # imported lazily to keep startup fast

        client = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"down: {exc.__class__.__name__}"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="school-erp",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        database=await _check_db(),
        redis=await _check_redis(),
        uploads_dir=str(settings.UPLOAD_DIR),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/livez")
async def livez() -> dict:
    """Process-alive ping. Never touches dependencies."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict:
    """Deep readiness check. Returns 503 if DB or Redis is unreachable."""
    db = await _check_db()
    redis = await _check_redis()
    if db != "ok" or redis != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"database": db, "redis": redis},
        )
    return {"status": "ready", "database": db, "redis": redis}
