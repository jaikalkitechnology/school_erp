"""FastAPI entrypoint for the Jaikalki School ERP backend."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.admin import router as admin_router
from app.api.v1 import router as v1_router
from app.config import settings
from app.core.file_storage import setup_upload_directory
from app.core.middleware import RequestContextMiddleware
from app.core.tenant import TenantMiddleware


log = logging.getLogger(__name__)


async def _retention_loop() -> None:
    """Background task: every 24h, delete notifications older than 30
    days. Runs in-process — no Celery dependency. The first sweep
    happens 60s after startup so app boot stays fast."""
    await asyncio.sleep(60)
    while True:
        try:
            from app.services.comms import sweep_old_notifications

            removed = await sweep_old_notifications(days=30)
            log.info("retention sweep: removed %s old notifications", removed)
        except Exception:  # pragma: no cover - never let this kill the worker
            log.exception("retention sweep failed")
        await asyncio.sleep(24 * 60 * 60)


async def _sync_rbac_catalogue() -> None:
    """On boot: replay the RBAC catalogue against every tenant. New
    role codes added to ``rbac_catalog.ROLES`` (eg. Phase 27's
    management / hod / office_admin / receptionist / accounts /
    payroll / data_entry_operator) get an actual row in every
    tenant's ``roles`` table so the admin Users panel can pick them
    immediately, without a manual re-seed.

    ``seed_rbac_for_tenant`` is idempotent — only missing rows get
    inserted. Existing role grants are refreshed to match the
    catalogue."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from app.services.seed import seed_rbac_for_tenant

    try:
        async with AsyncSessionLocal() as session:
            tenant_ids = [
                t for (t,) in (
                    await session.execute(select(Tenant.id))
                ).all()
            ]
            for tid in tenant_ids:
                try:
                    await seed_rbac_for_tenant(session, tid)
                except Exception:
                    log.exception("RBAC re-seed failed for tenant %s", tid)
        log.info("RBAC catalogue synced for %s tenants", len(tenant_ids))
    except Exception:
        log.exception("RBAC catalogue sync failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_upload_directory()
    # Replay RBAC so new role codes shipped in the catalogue land in
    # every tenant's roles table. Safe + idempotent — runs once per
    # boot before traffic starts hitting the API.
    await _sync_rbac_catalogue()
    # Daily notification retention sweep — keeps the inbox tidy.
    task = asyncio.create_task(_retention_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description="Multi-Tenant School ERP SaaS by Jaikalki Technology",
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Order matters: tenant context must be available to downstream handlers, and
# request-id must wrap *everything* so logs always carry it.
app.add_middleware(TenantMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id", "x-response-time-ms"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # In production, swap this for structured logging + Sentry capture.
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if not settings.DEBUG else f"{exc.__class__.__name__}: {exc}",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(v1_router)
app.include_router(admin_router)


@app.get("/", tags=["root"])
async def root() -> dict[str, Any]:
    return {
        "service": settings.APP_NAME,
        "company": settings.COMPANY_NAME,
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/v1/health",
    }
