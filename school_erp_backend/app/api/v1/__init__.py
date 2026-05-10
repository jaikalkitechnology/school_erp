"""Tenant-scoped public API (mobile + school admin web)."""

from fastapi import APIRouter

from app.api.v1 import auth, health, uploads

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(uploads.router)
