"""Exam + marks + grade-scale service (Phase 15)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import Section
from app.models.exams import (
    Exam,
    ExamMarks,
    ExamStatus,
    ExamSubject,
    GradeScale,
    MarkStatus,
)
from app.models.parent import Student
from app.schemas.exams import (
    ExamResults,
    ExamSubjectWrite,
    ExamWrite,
    GradeScaleWrite,
    MarkBulkRequest,
    ParentChildExamRow,
    ParentChildExams,
    SectionRoster,
    StudentExamResult,
    StudentSubjectResult,
)


def _D(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or "0"))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Exam CRUD -------------------------------------------------------------


async def list_exams(session: AsyncSession) -> list[Exam]:
    return list(
        (
            await session.execute(
                select(Exam).options(selectinload(Exam.subjects)).order_by(Exam.id.desc())
            )
        ).scalars().all()
    )


async def create_exam(session: AsyncSession, tenant_id: int, payload: ExamWrite) -> Exam:
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )
    obj = Exam(
        tenant_id=tenant_id,
        year_id=payload.year_id,
        term_id=payload.term_id,
        name=payload.name,
        kind=payload.kind.value,
        start_date=payload.start_date,
        end_date=payload.end_date,
        default_max_marks=payload.default_max_marks,
        status=ExamStatus.SCHEDULED.value if payload.start_date else ExamStatus.DRAFT.value,
        notes=payload.notes,
    )
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An exam with this name already exists for the academic year",
        )
    await session.refresh(obj)
    return obj


async def schedule_subject(
    session: AsyncSession,
    tenant_id: int,
    exam_id: int,
    payload: ExamSubjectWrite,
) -> ExamSubject:
    if payload.passing_marks > payload.max_marks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="passing_marks cannot exceed max_marks",
        )
    if (
        await session.execute(select(Exam).where(Exam.id == exam_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    obj = ExamSubject(
        tenant_id=tenant_id,
        exam_id=exam_id,
        class_def_id=payload.class_def_id,
        subject_id=payload.subject_id,
        max_marks=payload.max_marks,
        passing_marks=payload.passing_marks,
        exam_date=payload.exam_date,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subject already scheduled for this exam + class",
        )
    await session.refresh(obj)
    return obj


async def list_exam_subjects(session: AsyncSession, exam_id: int) -> list[ExamSubject]:
    return list(
        (
            await session.execute(
                select(ExamSubject)
                .where(ExamSubject.exam_id == exam_id)
                .order_by(ExamSubject.class_def_id, ExamSubject.subject_id)
            )
        ).scalars().all()
    )


# ---- Marks entry -----------------------------------------------------------


async def section_roster(
    session: AsyncSession, exam_subject_id: int, section_id: int
) -> SectionRoster:
    es = (
        await session.execute(select(ExamSubject).where(ExamSubject.id == exam_subject_id))
    ).scalar_one_or_none()
    if es is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam subject not found")

    students = list(
        (
            await session.execute(
                select(Student).where(
                    Student.section_id == section_id,
                    Student.class_def_id == es.class_def_id,
                    Student.is_active.is_(True),
                ).order_by(Student.full_name)
            )
        ).scalars().all()
    )
    saved = {
        m.student_id: m
        for m in (
            await session.execute(
                select(ExamMarks).where(ExamMarks.exam_subject_id == exam_subject_id)
            )
        ).scalars().all()
    }
    rows = []
    names: dict[int, str] = {}
    for s in students:
        names[s.id] = s.full_name
        m = saved.get(s.id)
        rows.append(
            {
                "student_id": s.id,
                "obtained_marks": (m.obtained_marks if m else None),
                "status": (MarkStatus(m.status) if m else None),
                "remarks": (m.remarks if m else None),
            }
        )
    return SectionRoster(
        exam_subject_id=exam_subject_id,
        rows=rows,  # type: ignore[arg-type]
        max_marks=es.max_marks,
        passing_marks=es.passing_marks,
        student_names=names,
    )


async def upsert_marks(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: MarkBulkRequest,
) -> int:
    es = (
        await session.execute(select(ExamSubject).where(ExamSubject.id == payload.exam_subject_id))
    ).scalar_one_or_none()
    if es is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam subject not found")
    max_marks = _D(es.max_marks)
    passing = _D(es.passing_marks)

    # Validate all students belong to that class.
    student_ids = [e.student_id for e in payload.entries]
    valid_ids = set(
        (
            await session.execute(
                select(Student.id).where(
                    Student.id.in_(student_ids),
                    Student.class_def_id == es.class_def_id,
                )
            )
        ).scalars().all()
    )
    invalid = set(student_ids) - valid_ids
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Students {sorted(invalid)} are not in the exam's class",
        )

    existing = {
        m.student_id: m
        for m in (
            await session.execute(
                select(ExamMarks).where(ExamMarks.exam_subject_id == payload.exam_subject_id)
            )
        ).scalars().all()
    }

    written = 0
    for entry in payload.entries:
        obtained = entry.obtained_marks
        if obtained is not None:
            obtained = _D(obtained)
            if obtained < 0 or obtained > max_marks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"obtained_marks for student {entry.student_id} must be 0..{max_marks}",
                )
        if entry.status is not None:
            stat = entry.status.value
        elif obtained is None:
            stat = MarkStatus.ABSENT.value
        else:
            stat = MarkStatus.PASS.value if obtained >= passing else MarkStatus.FAIL.value

        row = existing.get(entry.student_id)
        if row is None:
            session.add(
                ExamMarks(
                    tenant_id=tenant_id,
                    exam_subject_id=payload.exam_subject_id,
                    student_id=entry.student_id,
                    obtained_marks=obtained,
                    status=stat,
                    remarks=entry.remarks,
                    entered_by_user_id=user_id,
                )
            )
        else:
            row.obtained_marks = obtained
            row.status = stat
            row.remarks = entry.remarks
            row.entered_by_user_id = user_id
        written += 1

    await session.commit()
    return written


# ---- Grade scales ----------------------------------------------------------


async def list_grade_scales(session: AsyncSession) -> list[GradeScale]:
    return list((await session.execute(select(GradeScale))).scalars().all())


async def upsert_grade_scale(
    session: AsyncSession, tenant_id: int, payload: GradeScaleWrite
) -> GradeScale:
    if not payload.bands:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bands required")
    bands = sorted(payload.bands, key=lambda b: b.min_pct, reverse=True)
    obj = (
        await session.execute(select(GradeScale).where(GradeScale.code == payload.code))
    ).scalar_one_or_none()
    if obj is None:
        obj = GradeScale(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            bands=[b.model_dump() for b in bands],
            is_default=payload.is_default,
        )
        session.add(obj)
    else:
        obj.name = payload.name
        obj.bands = [b.model_dump() for b in bands]
        obj.is_default = payload.is_default

    if obj.is_default:
        # Only one default at a time.
        await session.execute(
            GradeScale.__table__.update()
            .where(GradeScale.code != obj.code)
            .values(is_default=False)
        )
    await session.commit()
    await session.refresh(obj)
    return obj


def _grade_for_pct(scale: GradeScale, pct: float) -> Optional[str]:
    for b in scale.bands or []:
        if pct >= float(b["min_pct"]):
            return str(b["grade"])
    return None


async def _default_scale(session: AsyncSession) -> Optional[GradeScale]:
    return (
        await session.execute(
            select(GradeScale).where(GradeScale.is_default.is_(True)).limit(1)
        )
    ).scalar_one_or_none()


# ---- Results ---------------------------------------------------------------


async def section_results(
    session: AsyncSession, *, exam_id: int, section_id: int
) -> ExamResults:
    section = (
        await session.execute(select(Section).where(Section.id == section_id))
    ).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    exam_subjects = list(
        (
            await session.execute(
                select(ExamSubject).where(
                    ExamSubject.exam_id == exam_id,
                    ExamSubject.class_def_id == section.class_def_id,
                )
            )
        ).scalars().all()
    )
    if not exam_subjects:
        return ExamResults(
            exam_id=exam_id, section_id=section_id, students=[], section_average_pct=0.0
        )

    es_ids = [e.id for e in exam_subjects]
    subject_max = {e.id: _D(e.max_marks) for e in exam_subjects}
    subject_passing = {e.id: _D(e.passing_marks) for e in exam_subjects}
    subject_subject_id = {e.id: e.subject_id for e in exam_subjects}

    students = list(
        (
            await session.execute(
                select(Student).where(
                    Student.section_id == section_id,
                    Student.is_active.is_(True),
                ).order_by(Student.full_name)
            )
        ).scalars().all()
    )

    marks_rows = list(
        (
            await session.execute(
                select(ExamMarks).where(ExamMarks.exam_subject_id.in_(es_ids))
            )
        ).scalars().all()
    )
    by_student: dict[int, dict[int, ExamMarks]] = {}
    for m in marks_rows:
        by_student.setdefault(m.student_id, {})[m.exam_subject_id] = m

    scale = await _default_scale(session)

    student_results: list[StudentExamResult] = []
    for stu in students:
        rows: list[StudentSubjectResult] = []
        total_max = Decimal("0")
        total_obtained = Decimal("0")
        any_fail = False
        any_absent = False
        for es in exam_subjects:
            m = by_student.get(stu.id, {}).get(es.id)
            obtained = _D(m.obtained_marks) if (m and m.obtained_marks is not None) else None
            if m is None:
                stat = MarkStatus.ABSENT
                any_absent = True
            else:
                stat = MarkStatus(m.status)
                if stat == MarkStatus.FAIL:
                    any_fail = True
                elif stat == MarkStatus.ABSENT:
                    any_absent = True
            sub_max = subject_max[es.id]
            total_max += sub_max
            if obtained is not None:
                total_obtained += obtained
            grade = None
            if scale and obtained is not None and sub_max > 0:
                grade = _grade_for_pct(scale, float((obtained / sub_max) * 100))
            rows.append(
                StudentSubjectResult(
                    subject_id=subject_subject_id[es.id],
                    max_marks=sub_max,
                    obtained=obtained,
                    status=stat,
                    grade=grade,
                )
            )
        pct = float((total_obtained / total_max) * 100) if total_max > 0 else 0.0
        overall_status = (
            MarkStatus.ABSENT if any_absent
            else MarkStatus.FAIL if any_fail
            else MarkStatus.PASS
        )
        overall_grade = _grade_for_pct(scale, pct) if scale else None
        student_results.append(
            StudentExamResult(
                student_id=stu.id,
                full_name=stu.full_name,
                admission_number=stu.admission_number,
                subjects=rows,
                total_max=total_max,
                total_obtained=total_obtained,
                percentage=round(pct, 2),
                overall_grade=overall_grade,
                rank_in_section=None,
                overall_status=overall_status,
            )
        )

    # Rank by total_obtained desc; ties get the same rank.
    ranked = sorted(student_results, key=lambda r: -float(r.total_obtained))
    last_score = None
    last_rank = 0
    for i, r in enumerate(ranked, start=1):
        score = float(r.total_obtained)
        if last_score is None or score < last_score:
            last_rank = i
            last_score = score
        r.rank_in_section = last_rank

    avg = (
        sum(r.percentage for r in student_results) / len(student_results)
        if student_results else 0.0
    )

    return ExamResults(
        exam_id=exam_id,
        section_id=section_id,
        students=student_results,
        section_average_pct=round(avg, 2),
    )


async def publish_exam(session: AsyncSession, exam_id: int) -> Exam:
    exam = (
        await session.execute(select(Exam).where(Exam.id == exam_id))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    exam.status = ExamStatus.PUBLISHED.value
    exam.published_at = _now()
    await session.commit()
    await session.refresh(exam)
    return exam


# ---- Parent view -----------------------------------------------------------


async def parent_child_results(
    session: AsyncSession, student_id: int
) -> ParentChildExams:
    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None or student.section_id is None:
        return ParentChildExams(student_id=student_id, rows=[])

    exams = list((await session.execute(select(Exam))).scalars().all())
    out: list[ParentChildExamRow] = []
    scale = await _default_scale(session)
    for exam in exams:
        es_rows = list(
            (
                await session.execute(
                    select(ExamSubject).where(
                        ExamSubject.exam_id == exam.id,
                        ExamSubject.class_def_id == student.class_def_id,
                    )
                )
            ).scalars().all()
        )
        if not es_rows:
            continue
        es_ids = [e.id for e in es_rows]
        marks = list(
            (
                await session.execute(
                    select(ExamMarks).where(
                        ExamMarks.exam_subject_id.in_(es_ids),
                        ExamMarks.student_id == student.id,
                    )
                )
            ).scalars().all()
        )
        if not marks and exam.status != ExamStatus.PUBLISHED.value:
            continue
        total_max = sum((_D(e.max_marks) for e in es_rows), Decimal("0"))
        total_obt = sum(
            (_D(m.obtained_marks) for m in marks if m.obtained_marks is not None),
            Decimal("0"),
        )
        pct = float((total_obt / total_max) * 100) if total_max > 0 else 0.0
        any_fail = any(MarkStatus(m.status) == MarkStatus.FAIL for m in marks)
        all_absent = marks and all(MarkStatus(m.status) == MarkStatus.ABSENT for m in marks)
        if all_absent:
            overall = MarkStatus.ABSENT
        elif any_fail:
            overall = MarkStatus.FAIL
        else:
            overall = MarkStatus.PASS
        out.append(
            ParentChildExamRow(
                exam_id=exam.id,
                exam_name=exam.name,
                published=exam.status == ExamStatus.PUBLISHED.value,
                total_max=total_max,
                total_obtained=total_obt,
                percentage=round(pct, 2),
                overall_grade=_grade_for_pct(scale, pct) if scale else None,
                overall_status=overall,
            )
        )
    return ParentChildExams(student_id=student_id, rows=out)
