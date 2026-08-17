"""Homework service (Phase 14)."""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Section
from app.models.homework import Homework, HomeworkSubmission, SubmissionStatus
from app.models.parent import Student
from app.schemas.homework import (
    GradeWrite,
    HomeworkStatusReport,
    HomeworkUpdate,
    HomeworkWrite,
    StudentHomeworkRow,
    StudentSubmissionStatus,
    SubmissionWrite,
)


def _today() -> _date:
    return datetime.now(timezone.utc).date()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Teacher / school admin -----------------------------------------------


async def list_for_section(
    session: AsyncSession,
    *,
    section_id: int,
    upcoming_only: bool = False,
) -> list[Homework]:
    stmt = (
        select(Homework)
        .where(Homework.section_id == section_id)
        .order_by(Homework.due_date.desc())
    )
    if upcoming_only:
        stmt = stmt.where(Homework.due_date >= _today())
    return list((await session.execute(stmt)).scalars().all())


async def list_for_teacher(session: AsyncSession, teacher_user_id: int) -> list[Homework]:
    return list(
        (
            await session.execute(
                select(Homework)
                .where(Homework.teacher_user_id == teacher_user_id)
                .order_by(Homework.due_date.desc())
            )
        ).scalars().all()
    )


async def create_homework(
    session: AsyncSession,
    *,
    tenant_id: int,
    teacher_user_id: int,
    payload: HomeworkWrite,
) -> Homework:
    if (
        await session.execute(select(Section).where(Section.id == payload.section_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if payload.due_date < (payload.assigned_on or _today()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="due_date must be on or after assigned_on",
        )
    obj = Homework(
        tenant_id=tenant_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        teacher_user_id=teacher_user_id,
        title=payload.title,
        description=payload.description,
        assigned_on=payload.assigned_on or _today(),
        due_date=payload.due_date,
        max_marks=payload.max_marks,
        attachments=list(payload.attachments),
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)

    # Notify every parent of every student in the section. Best-effort:
    # the homework is already saved, so a notify() blow-up shouldn't 500
    # the caller — they'll see it via the standard in-app feed anyway.
    try:
        await _notify_parents_homework_assigned(
            session, tenant_id=tenant_id, homework=obj,
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception(
            "homework.assigned notify failed (homework_id=%s)", obj.id,
        )
    return obj


async def _notify_parents_homework_assigned(
    session: AsyncSession, *, tenant_id: int, homework: Homework,
) -> None:
    """Fan the new homework out to the parents of every student in the
    section. Subject lookup is best-effort — falls back to "Homework"
    if the subject id isn't set."""
    from app.models.auth import User
    from app.models.parent import Parent, ParentChildMapping
    from app.services.comms import notify

    student_ids = [
        sid for (sid,) in (
            await session.execute(
                select(Student.id).where(Student.section_id == homework.section_id)
            )
        ).all()
    ]
    if not student_ids:
        return

    parent_user_ids = [
        uid for (uid,) in (
            await session.execute(
                select(User.id)
                .join(Parent, Parent.user_id == User.id)
                .join(ParentChildMapping, ParentChildMapping.parent_id == Parent.id)
                .where(
                    ParentChildMapping.student_id.in_(student_ids),
                    User.is_active.is_(True),
                )
            )
        ).all()
    ]
    if not parent_user_ids:
        return

    users = list((await session.execute(
        select(User).where(User.id.in_(parent_user_ids))
    )).scalars().all())

    subject_name = "Homework"
    if homework.subject_id is not None:
        try:
            from app.models.academic import Subject
            row = (
                await session.execute(
                    select(Subject.name).where(Subject.id == homework.subject_id)
                )
            ).first()
            if row:
                subject_name = row[0]
        except Exception:  # noqa: BLE001
            pass

    await notify(
        session,
        tenant_id=tenant_id,
        template_code="homework.assigned",
        recipients=users,
        context={
            "title": homework.title,
            "subject": subject_name,
            "due_date": homework.due_date.isoformat(),
        },
        deeplink=f"/homework/{homework.id}",
        source_type="homework",
        source_id=homework.id,
        kind="homework",
    )


async def update_homework(
    session: AsyncSession, homework_id: int, payload: HomeworkUpdate
) -> Homework:
    obj = (
        await session.execute(select(Homework).where(Homework.id == homework_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_homework(session: AsyncSession, homework_id: int) -> None:
    obj = (
        await session.execute(select(Homework).where(Homework.id == homework_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
    await session.delete(obj)
    await session.commit()


# ---- Submission ------------------------------------------------------------


async def submit_homework(
    session: AsyncSession,
    *,
    tenant_id: int,
    student_id: int,
    submitted_by_user_id: int,
    payload: SubmissionWrite,
) -> HomeworkSubmission:
    homework = (
        await session.execute(select(Homework).where(Homework.id == payload.homework_id))
    ).scalar_one_or_none()
    if homework is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")

    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if student.section_id != homework.section_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is not in this homework's section",
        )

    is_late = _today() > homework.due_date
    submission_status = (
        SubmissionStatus.LATE.value if is_late else SubmissionStatus.SUBMITTED.value
    )

    existing = (
        await session.execute(
            select(HomeworkSubmission).where(
                HomeworkSubmission.homework_id == payload.homework_id,
                HomeworkSubmission.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    now = _now()
    if existing is None:
        existing = HomeworkSubmission(
            tenant_id=tenant_id,
            homework_id=payload.homework_id,
            student_id=student_id,
            submitted_at=now,
            content=payload.content,
            attachments=list(payload.attachments),
            status=submission_status,
            submitted_by_user_id=submitted_by_user_id,
        )
        session.add(existing)
    else:
        if existing.status == SubmissionStatus.GRADED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Submission already graded; cannot re-submit",
            )
        existing.submitted_at = now
        existing.content = payload.content
        existing.attachments = list(payload.attachments)
        existing.status = submission_status
        existing.submitted_by_user_id = submitted_by_user_id
    await session.commit()
    await session.refresh(existing)
    return existing


async def grade_submission(
    session: AsyncSession,
    *,
    submission_id: int,
    teacher_user_id: int,
    payload: GradeWrite,
) -> HomeworkSubmission:
    sub = (
        await session.execute(
            select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    homework = (
        await session.execute(select(Homework).where(Homework.id == sub.homework_id))
    ).scalar_one()
    if payload.marks > Decimal(homework.max_marks or 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Marks exceed max_marks ({homework.max_marks})",
        )
    sub.marks = payload.marks
    sub.feedback = payload.feedback
    sub.status = SubmissionStatus.GRADED.value
    sub.graded_by_user_id = teacher_user_id
    sub.graded_at = _now()
    await session.commit()
    await session.refresh(sub)

    try:
        await _notify_homework_graded(
            session, tenant_id=homework.tenant_id, submission=sub, homework=homework,
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception(
            "homework.graded notify failed (submission_id=%s)", sub.id,
        )
    return sub


async def _notify_homework_graded(
    session: AsyncSession, *, tenant_id: int,
    submission: HomeworkSubmission, homework: Homework,
) -> None:
    """Tell every parent of this student that the paper was graded."""
    from app.models.auth import User
    from app.models.parent import Parent, ParentChildMapping
    from app.services.comms import notify

    student = (
        await session.execute(
            select(Student).where(Student.id == submission.student_id)
        )
    ).scalar_one_or_none()
    if student is None:
        return

    parent_user_ids = [
        uid for (uid,) in (
            await session.execute(
                select(User.id)
                .join(Parent, Parent.user_id == User.id)
                .join(ParentChildMapping, ParentChildMapping.parent_id == Parent.id)
                .where(
                    ParentChildMapping.student_id == student.id,
                    User.is_active.is_(True),
                )
            )
        ).all()
    ]
    if not parent_user_ids:
        return

    users = list((await session.execute(
        select(User).where(User.id.in_(parent_user_ids))
    )).scalars().all())

    await notify(
        session,
        tenant_id=tenant_id,
        template_code="homework.graded",
        recipients=users,
        context={
            "title": homework.title,
            "student": student.full_name,
            "marks": str(submission.marks) if submission.marks is not None else "—",
            "max_marks": str(homework.max_marks or "—"),
        },
        deeplink=f"/homework/{homework.id}/submissions/{submission.id}",
        source_type="homework_submission",
        source_id=submission.id,
        kind="homework",
    )


async def list_submissions(
    session: AsyncSession, homework_id: int
) -> list[HomeworkSubmission]:
    return list(
        (
            await session.execute(
                select(HomeworkSubmission)
                .where(HomeworkSubmission.homework_id == homework_id)
                .order_by(HomeworkSubmission.submitted_at.desc())
            )
        ).scalars().all()
    )


# ---- Reports ---------------------------------------------------------------


async def homework_status_report(
    session: AsyncSession, homework_id: int
) -> HomeworkStatusReport:
    homework = (
        await session.execute(select(Homework).where(Homework.id == homework_id))
    ).scalar_one_or_none()
    if homework is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")

    students = list(
        (
            await session.execute(
                select(Student)
                .where(Student.section_id == homework.section_id, Student.is_active.is_(True))
                .order_by(Student.full_name)
            )
        ).scalars().all()
    )
    subs = {
        s.student_id: s
        for s in (
            await session.execute(
                select(HomeworkSubmission).where(HomeworkSubmission.homework_id == homework_id)
            )
        ).scalars().all()
    }
    rows = [
        StudentSubmissionStatus(
            student_id=stu.id,
            full_name=stu.full_name,
            admission_number=stu.admission_number,
            submitted=stu.id in subs,
            submitted_at=subs[stu.id].submitted_at if stu.id in subs else None,
            status=(
                SubmissionStatus(subs[stu.id].status)
                if stu.id in subs
                else (
                    SubmissionStatus.MISSING
                    if homework.due_date < _today()
                    else None
                )
            ),
            marks=subs[stu.id].marks if stu.id in subs else None,
        )
        for stu in students
    ]
    submitted = sum(1 for r in rows if r.submitted)
    return HomeworkStatusReport(
        homework_id=homework.id,
        section_id=homework.section_id,
        title=homework.title,
        due_date=homework.due_date,
        max_marks=homework.max_marks,
        rows=rows,
        submitted_count=submitted,
        total_students=len(students),
    )


# ---- Parent / student facing ----------------------------------------------


async def list_for_student(
    session: AsyncSession, student_id: int
) -> list[StudentHomeworkRow]:
    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        return []
    if student.section_id is not None:
        # Normal path: homework posted to the child's exact section.
        section_filter = Homework.section_id == student.section_id
    elif student.class_def_id is not None:
        # The child has a class but no section assigned yet — a very common
        # data gap that would otherwise leave the parent with an empty
        # homework screen forever. Fall back to every section of that class
        # so homework for the class the child belongs to still shows up.
        section_ids = [
            sid
            for (sid,) in (
                await session.execute(
                    select(Section.id).where(
                        Section.class_def_id == student.class_def_id
                    )
                )
            ).all()
        ]
        if not section_ids:
            return []
        section_filter = Homework.section_id.in_(section_ids)
    else:
        # No section and no class — nothing to match on.
        return []
    homeworks = list(
        (
            await session.execute(
                select(Homework)
                .where(section_filter)
                .order_by(Homework.due_date.desc())
            )
        ).scalars().all()
    )
    if not homeworks:
        return []
    sub_by_hw = {
        s.homework_id: s
        for s in (
            await session.execute(
                select(HomeworkSubmission).where(
                    HomeworkSubmission.student_id == student_id,
                    HomeworkSubmission.homework_id.in_([h.id for h in homeworks]),
                )
            )
        ).scalars().all()
    }
    today = _today()

    # Resolve subject names in one round-trip so the parent UI can render
    # "Mathematics" instead of an opaque ID.
    subject_ids = {h.subject_id for h in homeworks if h.subject_id is not None}
    subject_names: dict[int, str] = {}
    if subject_ids:
        from app.models.academic import Subject  # local import: avoids cycles
        rows = (
            await session.execute(
                select(Subject.id, Subject.name).where(Subject.id.in_(subject_ids))
            )
        ).all()
        subject_names = {sid: name for sid, name in rows}

    out: list[StudentHomeworkRow] = []
    for h in homeworks:
        sub = sub_by_hw.get(h.id)
        if sub is not None:
            stat: Optional[SubmissionStatus] = SubmissionStatus(sub.status)
        elif h.due_date < today:
            stat = SubmissionStatus.MISSING
        else:
            stat = None
        out.append(
            StudentHomeworkRow(
                homework_id=h.id,
                title=h.title,
                description=h.description,
                assigned_on=h.assigned_on,
                due_date=h.due_date,
                subject_id=h.subject_id,
                subject_name=subject_names.get(h.subject_id) if h.subject_id else None,
                max_marks=h.max_marks,
                teacher_attachments=list(h.attachments or []),
                submission_status=stat,
                submitted=sub is not None,
                submitted_at=sub.submitted_at.date() if (sub and sub.submitted_at) else None,
                submission_content=sub.content if sub else None,
                submission_attachments=list(sub.attachments or []) if sub else [],
                marks=sub.marks if sub else None,
                feedback=sub.feedback if sub else None,
            )
        )
    return out


async def pending_homework_count(session: AsyncSession, student_id: int) -> int:
    """How many homework rows are still un-submitted for this student."""
    rows = await list_for_student(session, student_id)
    return sum(
        1
        for r in rows
        if not r.submitted
        and (r.submission_status is None or r.submission_status == SubmissionStatus.MISSING)
    )
