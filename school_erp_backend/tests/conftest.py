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


async def _truncate_all() -> None:
    """Wipe everything for tests that need a clean slate."""
    from sqlalchemy import delete

    from app.database import AsyncSessionLocal
    from app.models.academic import (
        AcademicTerm,
        AcademicYear,
        ClassDef,
        ClassSubject,
        Department,
        Holiday,
        Section,
        Subject,
    )
    from app.models.attendance import StudentAttendance
    from app.models.audit import AuditLog
    from app.models.exams import Exam, ExamMarks, ExamSubject, GradeScale
    from app.models.report_cards import (
        CoCurricularGrade,
        ReportCard,
        ReportCardRemark,
        ReportCardTemplate,
    )
    from app.models.homework import Homework, HomeworkSubmission
    from app.models.library import Book, BookCopy, Loan, Reservation
    from app.models.timetable import PeriodDef, Substitution, TimetableEntry
    from app.models.comms import (
        Announcement,
        Message,
        Notification,
        NotificationOutbox,
        NotificationTemplate,
    )
    from app.models.fees import (
        FeeCategory,
        FeeDiscount,
        FeeInvoice,
        FeePayment,
        FeeStructure,
    )
    from app.models.auth import (
        Permission,
        RefreshToken,
        Role,
        RolePermission,
        User,
        UserRole,
    )
    from app.models.curriculum import (
        CalendarEvent,
        Chapter,
        House,
        SectionSubject,
        Syllabus,
    )
    from app.models.parent import (
        LeaveApplication,
        Parent,
        ParentChildMapping,
        ParentSession,
        Student,
    )
    from app.models.sis import Admission, StudentDocument
    from app.models.teacher import Teacher, TeacherAttendance, TeacherSubject
    from app.models.tenant import (
        Subscription,
        SubscriptionPlan,
        Tenant,
        TenantSettings,
        TenantUsageSnapshot,
    )

    async with AsyncSessionLocal() as session:
        # Order matters - children before parents.
        for model in (
            # Phase 5
            Chapter, Syllabus, CalendarEvent, SectionSubject, House,
            # Phase 4
            Holiday, ClassSubject, Section, ClassDef, Subject,
            AcademicTerm, AcademicYear, Department,
            # Phase 3
            AuditLog,
            # Phase 7
            TeacherAttendance, TeacherSubject, Teacher,
            # Phase 6
            StudentDocument, Admission,
            # Phase 17
            Reservation, Loan, BookCopy, Book,
            # Phase 16
            ReportCard, ReportCardRemark, CoCurricularGrade, ReportCardTemplate,
            # Phase 15
            ExamMarks, ExamSubject, Exam, GradeScale,
            # Phase 14
            HomeworkSubmission, Homework,
            # Phase 13
            Substitution, TimetableEntry, PeriodDef,
            # Phase 12
            NotificationOutbox, Notification, Message, Announcement, NotificationTemplate,
            # Phase 11
            FeePayment, FeeInvoice, FeeStructure, FeeCategory, FeeDiscount,
            # Phase 9
            StudentAttendance,
            # Phase 8
            LeaveApplication,
            # Phase 2
            ParentSession, ParentChildMapping, Parent, Student,
            RefreshToken, UserRole, RolePermission, Permission, Role, User,
            # Phase 1
            TenantUsageSnapshot, TenantSettings, Subscription, Tenant, SubscriptionPlan,
        ):
            await session.execute(delete(model))
        await session.commit()


@pytest_asyncio.fixture
async def seeded_plans():
    """Truncate everything and seed plans fresh."""
    from app.database import AsyncSessionLocal
    from app.services.seed import seed_plans

    await _truncate_all()
    async with AsyncSessionLocal() as session:
        await seed_plans(session)
    yield


@pytest_asyncio.fixture
async def super_admin_token():
    """Run the full seed, then issue a real super-admin access token."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.services.seed import (
        DEFAULT_SUPER_ADMIN_EMAIL,
        DEFAULT_SUPER_ADMIN_PASSWORD,
        run_all,
    )

    await _truncate_all()
    await run_all()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SUPER_ADMIN_EMAIL,
                "password": DEFAULT_SUPER_ADMIN_PASSWORD,
                "subdomain": "platform",
            },
        )
        assert r.status_code == 200, r.text
        return r.json()["tokens"]["access_token"]


@pytest_asyncio.fixture
async def auth_client(super_admin_token):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        yield ac
