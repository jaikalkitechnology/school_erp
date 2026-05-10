"""Tenant-scoped public API (mobile + school admin web)."""

from fastapi import APIRouter

from app.api.v1 import (
    attendance,
    auth,
    curriculum,
    fees,
    health,
    notifications,
    parent,
    school_admin,
    sis,
    teachers,
    uploads,
)

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(uploads.router)
router.include_router(school_admin.router)
router.include_router(curriculum.router)
router.include_router(sis.router)
router.include_router(sis.admissions_router)
router.include_router(teachers.router)
router.include_router(parent.router)
router.include_router(parent.sa_router)
router.include_router(attendance.router)
router.include_router(notifications.router)
router.include_router(fees.router)
router.include_router(fees.parent_router)
