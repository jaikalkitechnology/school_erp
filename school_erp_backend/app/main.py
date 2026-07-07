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


async def _library_daily_notifications_loop() -> None:
    """Background task: once every 24h, sweep across every tenant and
    fire the two time-based library notifications:

      * **due_soon**   — loans still ACTIVE whose ``due_on`` is
                         exactly 2 calendar days from today.
      * **overdue_day7** — loans in OVERDUE status whose ``due_on``
                           is exactly 7 days ago.

    Runs in-process. The first sweep happens 120s after boot so the
    RBAC + template seed above have already finished. In-flight
    errors log-and-continue — a broken tenant must not kill the
    task for everyone else."""
    from datetime import date, timedelta

    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.library import Loan, LoanStatus
    from app.models.tenant import Tenant
    from app.services.library_notifications import fanout_for_loan

    await asyncio.sleep(120)
    while True:
        try:
            today = date.today()
            due_soon_target = today + timedelta(days=2)
            overdue_day7_target = today - timedelta(days=7)

            async with AsyncSessionLocal() as session:
                tenants = [
                    t for (t,) in (
                        await session.execute(select(Tenant.id))
                    ).all()
                ]
                due_soon_sent = 0
                overdue_day7_sent = 0
                for tid in tenants:
                    try:
                        due_soon_loans = list(
                            (
                                await session.execute(
                                    select(Loan).where(
                                        Loan.tenant_id == tid,
                                        Loan.status == LoanStatus.ACTIVE.value,
                                        Loan.due_on == due_soon_target,
                                    )
                                )
                            ).scalars().all()
                        )
                        for l in due_soon_loans:
                            await fanout_for_loan(
                                session,
                                tenant_id=tid,
                                template_code="library.due_soon",
                                loan=l,
                            )
                            due_soon_sent += 1

                        overdue_day7_loans = list(
                            (
                                await session.execute(
                                    select(Loan).where(
                                        Loan.tenant_id == tid,
                                        Loan.status == LoanStatus.OVERDUE.value,
                                        Loan.due_on == overdue_day7_target,
                                    )
                                )
                            ).scalars().all()
                        )
                        for l in overdue_day7_loans:
                            await fanout_for_loan(
                                session,
                                tenant_id=tid,
                                template_code="library.overdue_day7",
                                loan=l,
                            )
                            overdue_day7_sent += 1
                    except Exception:
                        log.exception(
                            "library daily notifications failed for tenant %s",
                            tid,
                        )
                log.info(
                    "library daily notifications: %s due-soon, %s day-7 overdue",
                    due_soon_sent, overdue_day7_sent,
                )
        except Exception:  # pragma: no cover
            log.exception("library daily notifications loop error")
        await asyncio.sleep(24 * 60 * 60)


async def _sync_rbac_catalogue() -> None:
    """On boot: replay the RBAC catalogue against every tenant. New
    role codes added to ``rbac_catalog.ROLES`` (currently: hod,
    receptionist) get an actual row in every tenant's ``roles`` table
    so the admin Users panel can pick them immediately, without a
    manual re-seed.

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
                # Library notification templates ride the same boot
                # sync — idempotent, only inserts missing rows so
                # librarian edits made on the Notifications page
                # survive.
                try:
                    from app.services.library_notifications import (
                        seed_library_templates,
                    )
                    await seed_library_templates(session, tid)
                except Exception:
                    log.exception(
                        "Library template seed failed for tenant %s", tid,
                    )
        log.info("RBAC catalogue synced for %s tenants", len(tenant_ids))
    except Exception:
        log.exception("RBAC catalogue sync failed")

    # Backfill: refresh granted_admin_pages against the current
    # DEFAULT_PAGES_BY_ROLE for any user we can safely treat as
    # "still on defaults". This covers two cases:
    #
    #   1. User was created before their role had defaults —
    #      granted_admin_pages is empty.
    #   2. User was created when their role had an older default set
    #      that has since evolved (eg. Librarian's default was once
    #      ``[dashboard, library, reports]`` before the Library split
    #      shipped seven new sub-page slugs). We detect the stale
    #      default by checking that the user's current grants are a
    #      subset of the union of every catalogued default for their
    #      roles — meaning nothing was manually added by the school
    #      admin. Manually-customised users (who have grants outside
    #      the role defaults) are left alone.
    try:
        from app.core.admin_pages import DEFAULT_PAGES_BY_ROLE
        from app.models.auth import Role, User, UserRole

        async with AsyncSessionLocal() as session:
            users_with_roles = (
                await session.execute(
                    select(User, Role.code)
                    .join(UserRole, UserRole.user_id == User.id)
                    .join(Role, Role.id == UserRole.role_id)
                )
            ).all()
            touched = 0
            by_user: dict[int, tuple[User, list[str]]] = {}
            for user, code in users_with_roles:
                if user.id not in by_user:
                    by_user[user.id] = (user, [])
                by_user[user.id][1].append(code)

            for user, codes in by_user.values():
                default_slugs: set[str] = set()
                for code in codes:
                    for slug in DEFAULT_PAGES_BY_ROLE.get(code, ()):
                        default_slugs.add(slug)
                if not default_slugs:
                    continue
                current = set(user.granted_admin_pages or [])
                # Skip users whose grants include something outside
                # the role defaults — they've been customised.
                if current and not current.issubset(default_slugs):
                    continue
                target = sorted(default_slugs)
                if list(current) and sorted(current) == target:
                    continue
                user.granted_admin_pages = target
                touched += 1
            if touched:
                await session.commit()
                log.info(
                    "granted_admin_pages refreshed for %s users", touched,
                )
    except Exception:
        log.exception("granted_admin_pages backfill failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_upload_directory()
    # Replay RBAC so new role codes shipped in the catalogue land in
    # every tenant's roles table. Safe + idempotent — runs once per
    # boot before traffic starts hitting the API.
    await _sync_rbac_catalogue()
    # Daily notification retention sweep — keeps the inbox tidy.
    retention_task = asyncio.create_task(_retention_loop())
    # Daily due-soon + overdue-day-7 library push loop.
    lib_task = asyncio.create_task(_library_daily_notifications_loop())
    try:
        yield
    finally:
        for t in (retention_task, lib_task):
            t.cancel()
            try:
                await t
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
