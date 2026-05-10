"""FastAPI entrypoint for the Jaikalki School ERP backend."""

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


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_upload_directory()
    yield


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
