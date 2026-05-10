"""Health probe used by load balancers and Phase 0 acceptance tests."""

from datetime import datetime, timezone

from fastapi import APIRouter
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
