"""Tenant-scoped public API (mobile + school admin web)."""

from fastapi import APIRouter

from app.api.v1 import (
    attendance,
    auth,
    comms,
    curriculum,
    fees,
    health,
    homework,
    parent,
    school_admin,
    sis,
    teachers,
    timetable,
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
router.include_router(fees.router)
router.include_router(fees.parent_router)
# Phase 12: real notifications + announcements + messages.
router.include_router(comms.sa_router)
router.include_router(comms.router)
router.include_router(comms.messages_router)
router.include_router(comms.notif_router)
router.include_router(timetable.router)
router.include_router(homework.router)
router.include_router(homework.parent_router)
