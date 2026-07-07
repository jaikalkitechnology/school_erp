"""Library → notifications glue.

Every library event that should reach a borrower (or their parents)
comes through here. We keep the concerns separate from
``services/library.py`` so the circulation logic stays readable and
the notification templates + fanout live in one place.

Templates are seeded once per tenant (see ``seed_library_templates``)
and rendered via the shared ``services/comms.notify`` pipeline —
same code path that the school-wide announcements + messages use.
"""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.comms import NotificationTemplate
from app.models.library import Book, BorrowerKind, Loan


# ---------------------------------------------------------------------------
# Template catalogue
# ---------------------------------------------------------------------------


# Every library.* template code the code below can render. Order
# matters — the notification-templates admin page renders them in
# this sequence so the librarian sees the flow chronologically.
LIBRARY_TEMPLATES: list[dict] = [
    {
        "code": "library.issued",
        "subject_en": "Book borrowed: {{title}}",
        "body_en": (
            "Hi {{borrower}}, you've borrowed \"{{title}}\". "
            "Due back on {{due}}. Fine after that: ₹{{fine_per_day}}/day."
        ),
        "channels": ["in_app", "push"],
    },
    {
        "code": "library.due_soon",
        "subject_en": "Due in 2 days: {{title}}",
        "body_en": (
            "Reminder — \"{{title}}\" is due on {{due}}. "
            "Renew from the app or return at the library desk."
        ),
        "channels": ["in_app", "push"],
    },
    {
        "code": "library.overdue_day1",
        "subject_en": "Overdue: {{title}}",
        "body_en": (
            "\"{{title}}\" was due on {{due}} and is now overdue. "
            "Fine so far: ₹{{fine}}. Please return it today."
        ),
        "channels": ["in_app", "push", "sms"],
    },
    {
        "code": "library.overdue_day7",
        "subject_en": "Second reminder: {{title}} is 7 days overdue",
        "body_en": (
            "\"{{title}}\" is 7 days overdue. Fine so far: ₹{{fine}}. "
            "Please contact the librarian if there's an issue."
        ),
        "channels": ["in_app", "push", "sms"],
    },
    {
        "code": "library.reservation_ready",
        "subject_en": "Your reservation is ready: {{title}}",
        "body_en": (
            "Good news, {{borrower}} — your reservation for \"{{title}}\" "
            "is ready at the library desk. Pick it up within 24 hours."
        ),
        "channels": ["in_app", "push"],
    },
]


async def seed_library_templates(session: AsyncSession, tenant_id: int) -> int:
    """Insert any missing library.* templates for the given tenant.
    Idempotent — existing rows are left as-is so librarian edits
    survive re-seeding."""
    existing = {
        code
        for (code,) in (
            await session.execute(
                select(NotificationTemplate.code).where(
                    NotificationTemplate.tenant_id == tenant_id,
                    NotificationTemplate.code.in_(
                        [t["code"] for t in LIBRARY_TEMPLATES]
                    ),
                )
            )
        ).all()
    }
    added = 0
    for spec in LIBRARY_TEMPLATES:
        if spec["code"] in existing:
            continue
        session.add(
            NotificationTemplate(
                tenant_id=tenant_id,
                code=spec["code"],
                subject_en=spec["subject_en"],
                body_en=spec["body_en"],
                channels=list(spec["channels"]),
                is_active=True,
            )
        )
        added += 1
    if added:
        await session.commit()
    return added


# ---------------------------------------------------------------------------
# Borrower → user resolution
# ---------------------------------------------------------------------------


async def borrower_users(
    session: AsyncSession,
    borrower_kind: str,
    borrower_id: int,
) -> list[User]:
    """Which User rows should receive a notification about this
    borrower?

    * Student loans go to the student's own login (if any) **and**
      every parent linked via ``parent_child_mappings`` — so the
      parent sees the reminder on their phone even if the student
      doesn't have an app account yet.
    * Teacher loans go to the teacher's own login only.
    """
    from app.models.parent import ParentChildMapping, Parent, Student
    from app.models.teacher import Teacher

    users: list[User] = []
    if borrower_kind == BorrowerKind.STUDENT.value:
        student = (
            await session.execute(
                select(Student).where(Student.id == borrower_id)
            )
        ).scalar_one_or_none()
        if student is None:
            return []
        if student.user_id is not None:
            u = (
                await session.execute(
                    select(User).where(User.id == student.user_id)
                )
            ).scalar_one_or_none()
            if u is not None and u.is_active:
                users.append(u)
        parent_ids = [
            pid for (pid,) in (
                await session.execute(
                    select(ParentChildMapping.parent_id).where(
                        ParentChildMapping.student_id == student.id,
                    )
                )
            ).all()
        ]
        if parent_ids:
            parent_user_ids = [
                uid for (uid,) in (
                    await session.execute(
                        select(Parent.user_id).where(
                            Parent.id.in_(parent_ids),
                            Parent.user_id.isnot(None),
                        )
                    )
                ).all()
                if uid is not None
            ]
            if parent_user_ids:
                parents = list(
                    (
                        await session.execute(
                            select(User).where(
                                User.id.in_(parent_user_ids),
                                User.is_active.is_(True),
                            )
                        )
                    ).scalars().all()
                )
                users.extend(parents)
    elif borrower_kind == BorrowerKind.TEACHER.value:
        teacher = (
            await session.execute(
                select(Teacher).where(Teacher.id == borrower_id)
            )
        ).scalar_one_or_none()
        if teacher is None or teacher.user_id is None:
            return []
        u = (
            await session.execute(
                select(User).where(User.id == teacher.user_id)
            )
        ).scalar_one_or_none()
        if u is not None and u.is_active:
            users.append(u)
    return users


# ---------------------------------------------------------------------------
# The one-shot fanout used by every trigger
# ---------------------------------------------------------------------------


async def _borrower_name(
    session: AsyncSession, borrower_kind: str, borrower_id: int,
) -> str:
    from app.models.parent import Student
    from app.models.teacher import Teacher

    if borrower_kind == BorrowerKind.STUDENT.value:
        s = (
            await session.execute(
                select(Student).where(Student.id == borrower_id)
            )
        ).scalar_one_or_none()
        return s.full_name if s else f"Student #{borrower_id}"
    t = (
        await session.execute(
            select(Teacher).where(Teacher.id == borrower_id)
        )
    ).scalar_one_or_none()
    return t.full_name if t else f"Teacher #{borrower_id}"


async def fanout_for_loan(
    session: AsyncSession,
    *,
    tenant_id: int,
    template_code: str,
    loan: Loan,
    extra_context: Optional[dict] = None,
) -> None:
    """Render + queue notifications for every user linked to the
    loan's borrower. Failures never propagate — a broken template or
    push provider must not roll back an issue / return."""
    from app.services.comms import notify
    from app.services.push_dispatch import drain_pending_push_outbox_ids

    try:
        book = (
            await session.execute(
                select(Book).where(Book.id == loan.book_id)
            )
        ).scalar_one_or_none()
        if book is None:
            return
        recipients = await borrower_users(
            session, loan.borrower_kind, loan.borrower_id,
        )
        if not recipients:
            return
        borrower = await _borrower_name(
            session, loan.borrower_kind, loan.borrower_id,
        )
        context = {
            "borrower": borrower,
            "title": book.title,
            "due": loan.due_on.isoformat() if loan.due_on else "",
            "fine": str(loan.fine_amount or 0),
            "fine_per_day": str(book.default_fine_per_day or 0),
        }
        if extra_context:
            context.update(extra_context)
        _, push_outbox_ids = await notify(
            session,
            tenant_id=tenant_id,
            template_code=template_code,
            recipients=recipients,
            context=context,
            deeplink=f"/library/loan/{loan.id}",
            source_type="library_loan",
            source_id=loan.id,
            kind="library",
        )
        if push_outbox_ids:
            await drain_pending_push_outbox_ids(session, push_outbox_ids)
    except Exception:
        # Notifications are best-effort — never fail the caller.
        import logging
        logging.getLogger(__name__).exception(
            "library notification fanout failed (template=%s loan=%s)",
            template_code, getattr(loan, "id", None),
        )


async def fanout_for_reservation_ready(
    session: AsyncSession,
    *,
    tenant_id: int,
    book: Book,
    borrower_kind: str,
    borrower_id: int,
    reservation_id: int,
) -> None:
    """Fired when a returned copy promotes a pending reservation to
    ``ready``. The reserving borrower gets a heads-up so they can
    swing by the desk."""
    from app.services.comms import notify
    from app.services.push_dispatch import drain_pending_push_outbox_ids

    try:
        recipients = await borrower_users(session, borrower_kind, borrower_id)
        if not recipients:
            return
        borrower_name = await _borrower_name(
            session, borrower_kind, borrower_id,
        )
        _, push_outbox_ids = await notify(
            session,
            tenant_id=tenant_id,
            template_code="library.reservation_ready",
            recipients=recipients,
            context={
                "borrower": borrower_name,
                "title": book.title,
            },
            deeplink=f"/library/reservation/{reservation_id}",
            source_type="library_reservation",
            source_id=reservation_id,
            kind="library",
        )
        if push_outbox_ids:
            await drain_pending_push_outbox_ids(session, push_outbox_ids)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "library reservation-ready fanout failed (reservation=%s)",
            reservation_id,
        )
