"""Tenant-scoped public API (mobile + school admin web)."""

from fastapi import APIRouter

from app.api.v1 import (
    admin_users,
    attendance,
    auth,
    comms,
    curriculum,
    exams,
    fees,
    health,
    homework,
    hostel,
    library,
    parent,
    principal,
    operations,
    operations_mobile,
    report_cards,
    school_admin,
    school_analytics,
    subscription,
    sis,
    student_app,
    coordinator,
    staff_app,
    staff_work,
    teacher_app,
    teachers,
    timetable,
    transport,
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
router.include_router(exams.router)
router.include_router(exams.grade_router)
router.include_router(exams.parent_router)
router.include_router(report_cards.router)
router.include_router(report_cards.parent_router)
router.include_router(library.router)
router.include_router(library.parent_router)
router.include_router(transport.router)
router.include_router(transport.parent_router)
router.include_router(hostel.router)
router.include_router(hostel.parent_router)
router.include_router(school_analytics.router)
router.include_router(subscription.router)
router.include_router(admin_users.router)
router.include_router(teacher_app.router)
router.include_router(staff_app.router)
router.include_router(staff_work.router)
router.include_router(coordinator.router)
router.include_router(principal.router)
router.include_router(operations.router)
router.include_router(operations_mobile.router)
router.include_router(student_app.router)
