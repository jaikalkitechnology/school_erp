"""Phase 5: curriculum, houses, calendar endpoints (tenant-scoped)."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.models.academic import Section, Subject
from app.models.curriculum import (
    CalendarEvent,
    Chapter,
    House,
    SectionSubject,
    Syllabus,
)
from app.schemas.curriculum import (
    CalendarEventRead,
    CalendarEventWrite,
    ChapterProgress,
    ChapterRead,
    ChapterWrite,
    HouseRead,
    HouseWrite,
    SectionSubjectBulkLink,
    SectionSubjectRead,
    SectionSubjectWrite,
    SyllabusRead,
    SyllabusWrite,
)


_school_staff = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher",
)
_school_admins = require_roles("school_admin", "principal", "vice_principal", "coordinator")


router = APIRouter(
    prefix="/school-admin/curriculum",
    tags=["school-admin"],
    dependencies=[Depends(_school_staff)],
)


async def _get_or_404(session: AsyncSession, model, item_id: int):
    obj = (await session.execute(select(model).where(model.id == item_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return obj


# ---- Houses ----------------------------------------------------------------


@router.get("/houses", response_model=list[HouseRead])
async def list_houses(session: AsyncSession = Depends(tenant_scoped_session)):
    return list((await session.execute(select(House).order_by(House.name))).scalars().all())


@router.post("/houses", response_model=HouseRead, status_code=status.HTTP_201_CREATED)
async def create_house(
    payload: HouseWrite,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = House(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/houses/{item_id}", response_model=HouseRead)
async def update_house(
    item_id: int,
    payload: HouseWrite,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, House, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/houses/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_house(
    item_id: int,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, House, item_id)
    await session.delete(obj)
    await session.commit()


# ---- Section subjects ------------------------------------------------------


@router.get("/section-subjects", response_model=list[SectionSubjectRead])
async def list_section_subjects(
    section_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    stmt = select(SectionSubject).order_by(SectionSubject.section_id, SectionSubject.subject_id)
    if section_id is not None:
        stmt = stmt.where(SectionSubject.section_id == section_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post(
    "/section-subjects", response_model=SectionSubjectRead, status_code=status.HTTP_201_CREATED
)
async def create_section_subject(
    payload: SectionSubjectWrite,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await _get_or_404(session, Section, payload.section_id)
    await _get_or_404(session, Subject, payload.subject_id)
    obj = SectionSubject(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/section-subjects/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section_subject(
    item_id: int,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, SectionSubject, item_id)
    await session.delete(obj)
    await session.commit()


@router.post("/section-subjects/bulk", response_model=list[SectionSubjectRead])
async def bulk_link_section_subjects(
    payload: SectionSubjectBulkLink,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Idempotent: any subject_id already linked is left alone."""
    await _get_or_404(session, Section, payload.section_id)
    existing = {
        ss.subject_id
        for ss in (
            await session.execute(
                select(SectionSubject).where(SectionSubject.section_id == payload.section_id)
            )
        ).scalars().all()
    }
    created: list[SectionSubject] = []
    for sid in payload.subject_ids:
        if sid in existing:
            continue
        ss = SectionSubject(
            tenant_id=principal.tenant_id,
            section_id=payload.section_id,
            subject_id=sid,
            weekly_periods=payload.weekly_periods,
        )
        session.add(ss)
        created.append(ss)
    if created:
        await session.commit()
        for ss in created:
            await session.refresh(ss)
    return list(
        (
            await session.execute(
                select(SectionSubject).where(SectionSubject.section_id == payload.section_id)
            )
        ).scalars().all()
    )


# ---- Calendar events -------------------------------------------------------


@router.get("/events", response_model=list[CalendarEventRead])
async def list_events(
    year_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    stmt = select(CalendarEvent).order_by(CalendarEvent.starts_at)
    if year_id is not None:
        stmt = stmt.where(CalendarEvent.year_id == year_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/events", response_model=CalendarEventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: CalendarEventWrite,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = CalendarEvent(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/events/{item_id}", response_model=CalendarEventRead)
async def update_event(
    item_id: int,
    payload: CalendarEventWrite,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, CalendarEvent, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/events/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    item_id: int,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, CalendarEvent, item_id)
    await session.delete(obj)
    await session.commit()


# ---- Syllabus + chapters ---------------------------------------------------


def _overall_pct(chapters: list[Chapter]) -> float:
    if not chapters:
        return 0.0
    total_periods = sum(c.expected_periods or 0 for c in chapters) or len(chapters)
    weighted = sum(
        (c.expected_periods or 1) * float(c.completion_pct or 0) for c in chapters
    )
    return round(weighted / total_periods, 2)


def _serialise_syllabus(s: Syllabus) -> SyllabusRead:
    chapters = [ChapterRead.model_validate(c) for c in (s.chapters or [])]
    return SyllabusRead(
        id=s.id,
        year_id=s.year_id,
        class_def_id=s.class_def_id,
        subject_id=s.subject_id,
        title=s.title,
        description=s.description,
        chapters=chapters,
        overall_completion_pct=_overall_pct(s.chapters or []),
    )


@router.get("/syllabi", response_model=list[SyllabusRead])
async def list_syllabi(
    year_id: Optional[int] = None,
    class_def_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    stmt = (
        select(Syllabus)
        .options(selectinload(Syllabus.chapters))
        .order_by(Syllabus.id.desc())
    )
    if year_id is not None:
        stmt = stmt.where(Syllabus.year_id == year_id)
    if class_def_id is not None:
        stmt = stmt.where(Syllabus.class_def_id == class_def_id)
    if subject_id is not None:
        stmt = stmt.where(Syllabus.subject_id == subject_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialise_syllabus(s) for s in rows]


@router.post("/syllabi", response_model=SyllabusRead, status_code=status.HTTP_201_CREATED)
async def create_syllabus(
    payload: SyllabusWrite,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = Syllabus(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj, attribute_names=["chapters"])
    return _serialise_syllabus(obj)


@router.delete("/syllabi/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_syllabus(
    item_id: int,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, Syllabus, item_id)
    await session.delete(obj)
    await session.commit()


@router.post(
    "/syllabi/{syllabus_id}/chapters",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_chapter(
    syllabus_id: int,
    payload: ChapterWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await _get_or_404(session, Syllabus, syllabus_id)
    obj = Chapter(tenant_id=principal.tenant_id, syllabus_id=syllabus_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/chapters/{chapter_id}/progress", response_model=ChapterRead)
async def set_chapter_progress(
    chapter_id: int,
    payload: ChapterProgress,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    chapter: Chapter = await _get_or_404(session, Chapter, chapter_id)
    chapter.completion_pct = Decimal(str(payload.completion_pct))
    chapter.completed_on = payload.completed_on
    if payload.completion_pct >= 100 and chapter.completed_on is None:
        from datetime import date as _date

        chapter.completed_on = _date.today()
    await session.commit()
    await session.refresh(chapter)
    return chapter


@router.delete("/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    chapter_id: int,
    principal: AuthPrincipal = Depends(_school_admins),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, Chapter, chapter_id)
    await session.delete(obj)
    await session.commit()
