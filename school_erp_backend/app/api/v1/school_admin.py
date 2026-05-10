"""School Admin endpoints (tenant-scoped).

Routes here are gated to school staff (school_admin / principal / vice_principal /
coordinator) and use ``tenant_scoped_session`` so every query is auto-filtered
by the caller's tenant.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.file_storage import get_tenant_storage_used_mb
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.academic import (
    AcademicTerm,
    AcademicYear,
    ClassDef,
    Department,
    Holiday,
    Section,
    Subject,
)
from app.models.auth import Role, User, UserRole
from app.models.parent import Student
from app.models.tenant import Tenant
from app.schemas.academic import (
    AcademicTermRead,
    AcademicTermWrite,
    AcademicYearRead,
    AcademicYearWrite,
    ClassDefRead,
    ClassDefWrite,
    DepartmentRead,
    DepartmentWrite,
    HolidayRead,
    HolidayWrite,
    SchoolDashboard,
    SchoolSettings,
    SchoolSettingsUpdate,
    SectionRead,
    SectionWrite,
    SubjectRead,
    SubjectWrite,
)


_school_staff = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator"
)


router = APIRouter(
    prefix="/school-admin",
    tags=["school-admin"],
    dependencies=[Depends(_school_staff)],
)


# ---- Dashboard --------------------------------------------------------------


async def _count(session: AsyncSession, model) -> int:
    return int((await session.execute(select(func.count(model.id)))).scalar_one())


@router.get("/dashboard", response_model=SchoolDashboard)
async def dashboard(
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    students = await _count(session, Student)
    departments = await _count(session, Department)
    classes = await _count(session, ClassDef)
    sections = await _count(session, Section)
    subjects = await _count(session, Subject)

    # Teacher count via UserRole join.
    teacher_role_ids = (
        await session.execute(
            select(Role.id).where(Role.code.in_(["class_teacher", "subject_teacher"]))
        )
    ).scalars().all()
    if teacher_role_ids:
        teachers = int(
            (
                await session.execute(
                    select(func.count(func.distinct(UserRole.user_id))).where(
                        UserRole.role_id.in_(list(teacher_role_ids))
                    )
                )
            ).scalar_one()
        )
    else:
        teachers = 0

    active_year_row = (
        await session.execute(
            select(AcademicYear)
            .options(selectinload(AcademicYear.terms))
            .where(AcademicYear.is_active.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()

    return SchoolDashboard(
        school_name=principal.tenant.school_name,
        subdomain=principal.tenant.subdomain,
        students_count=students,
        teachers_count=teachers,
        classes_count=classes,
        sections_count=sections,
        subjects_count=subjects,
        departments_count=departments,
        active_year=AcademicYearRead.model_validate(active_year_row) if active_year_row else None,
        storage_used_mb=round(get_tenant_storage_used_mb(principal.tenant_id), 2),
        storage_limit_mb=principal.tenant.storage_limit_mb,
    )


# ---- Settings ---------------------------------------------------------------


@router.get("/settings", response_model=SchoolSettings)
async def get_settings(principal: AuthPrincipal = Depends(_school_staff)):
    t = principal.tenant
    return SchoolSettings(
        school_name=t.school_name,
        primary_color=t.primary_color,
        secondary_color=t.secondary_color,
        logo_url=t.logo_url,
        timezone=t.timezone,
        affiliation_board=t.affiliation_board,
        medium=t.medium,
        address=t.address,
        city=t.city,
        state=t.state,
        pincode=t.pincode,
        phone=t.phone,
        email=t.email,
    )


@router.patch("/settings", response_model=SchoolSettings)
async def update_settings(
    payload: SchoolSettingsUpdate,
    principal: AuthPrincipal = Depends(require_roles("school_admin", "principal")),
    session: AsyncSession = Depends(platform_session),
):
    """Settings live on the Tenant row itself - we use the unfiltered platform
    session because Tenant is not a TenantBase model."""
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == principal.tenant_id))
    ).scalar_one()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await session.commit()
    await session.refresh(tenant)
    return SchoolSettings(
        school_name=tenant.school_name,
        primary_color=tenant.primary_color,
        secondary_color=tenant.secondary_color,
        logo_url=tenant.logo_url,
        timezone=tenant.timezone,
        affiliation_board=tenant.affiliation_board,
        medium=tenant.medium,
        address=tenant.address,
        city=tenant.city,
        state=tenant.state,
        pincode=tenant.pincode,
        phone=tenant.phone,
        email=tenant.email,
    )


# ---- Generic CRUD helpers --------------------------------------------------


async def _list_all(session: AsyncSession, model, order_by=None) -> list:
    stmt = select(model)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    return list((await session.execute(stmt)).scalars().all())


async def _get_or_404(session: AsyncSession, model, item_id: int):
    obj = (await session.execute(select(model).where(model.id == item_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return obj


# ---- Departments ------------------------------------------------------------


@router.get("/departments", response_model=list[DepartmentRead])
async def list_departments(session: AsyncSession = Depends(tenant_scoped_session)):
    return await _list_all(session, Department, order_by=Department.name)


@router.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = Department(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/departments/{item_id}", response_model=DepartmentRead)
async def update_department(
    item_id: int,
    payload: DepartmentWrite,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, Department, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/departments/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(item_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    obj = await _get_or_404(session, Department, item_id)
    await session.delete(obj)
    await session.commit()


# ---- Academic years + terms -------------------------------------------------


@router.get("/academic-years", response_model=list[AcademicYearRead])
async def list_academic_years(session: AsyncSession = Depends(tenant_scoped_session)):
    rows = (
        await session.execute(
            select(AcademicYear)
            .options(selectinload(AcademicYear.terms))
            .order_by(AcademicYear.start_date.desc())
        )
    ).scalars().all()
    return list(rows)


@router.post("/academic-years", response_model=AcademicYearRead, status_code=status.HTTP_201_CREATED)
async def create_academic_year(
    payload: AcademicYearWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    if payload.is_active:
        # Only one active year at a time.
        await session.execute(
            AcademicYear.__table__.update()
            .where(AcademicYear.tenant_id == principal.tenant_id)
            .values(is_active=False)
        )
    obj = AcademicYear(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj, attribute_names=["terms"])
    return obj


@router.post("/academic-years/{year_id}/activate", response_model=AcademicYearRead)
async def activate_academic_year(
    year_id: int,
    principal: AuthPrincipal = Depends(require_roles("school_admin", "principal")),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    year = await _get_or_404(session, AcademicYear, year_id)
    await session.execute(
        AcademicYear.__table__.update()
        .where(AcademicYear.tenant_id == principal.tenant_id)
        .values(is_active=False)
    )
    year.is_active = True
    await session.commit()
    await session.refresh(year, attribute_names=["terms"])
    return year


@router.post("/academic-years/{year_id}/terms", response_model=AcademicTermRead, status_code=status.HTTP_201_CREATED)
async def add_term(
    year_id: int,
    payload: AcademicTermWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await _get_or_404(session, AcademicYear, year_id)
    term = AcademicTerm(tenant_id=principal.tenant_id, year_id=year_id, **payload.model_dump())
    session.add(term)
    await session.commit()
    await session.refresh(term)
    return term


# ---- Classes ----------------------------------------------------------------


@router.get("/classes", response_model=list[ClassDefRead])
async def list_classes(session: AsyncSession = Depends(tenant_scoped_session)):
    return list(
        (
            await session.execute(
                select(ClassDef).order_by(ClassDef.sequence, ClassDef.code)
            )
        ).scalars().all()
    )


@router.post("/classes", response_model=ClassDefRead, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassDefWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = ClassDef(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/classes/{item_id}", response_model=ClassDefRead)
async def update_class(
    item_id: int,
    payload: ClassDefWrite,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, ClassDef, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/classes/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(item_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    obj = await _get_or_404(session, ClassDef, item_id)
    await session.delete(obj)
    await session.commit()


# ---- Sections ---------------------------------------------------------------


@router.get("/sections", response_model=list[SectionRead])
async def list_sections(
    class_def_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    stmt = select(Section).order_by(Section.class_def_id, Section.name)
    if class_def_id is not None:
        stmt = stmt.where(Section.class_def_id == class_def_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/sections", response_model=SectionRead, status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await _get_or_404(session, ClassDef, payload.class_def_id)
    obj = Section(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/sections/{item_id}", response_model=SectionRead)
async def update_section(
    item_id: int,
    payload: SectionWrite,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, Section, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/sections/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(item_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    obj = await _get_or_404(session, Section, item_id)
    await session.delete(obj)
    await session.commit()


# ---- Subjects ---------------------------------------------------------------


@router.get("/subjects", response_model=list[SubjectRead])
async def list_subjects(session: AsyncSession = Depends(tenant_scoped_session)):
    return list((await session.execute(select(Subject).order_by(Subject.code))).scalars().all())


@router.post("/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = Subject(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/subjects/{item_id}", response_model=SubjectRead)
async def update_subject(
    item_id: int,
    payload: SubjectWrite,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = await _get_or_404(session, Subject, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/subjects/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(item_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    obj = await _get_or_404(session, Subject, item_id)
    await session.delete(obj)
    await session.commit()


# ---- Holidays ---------------------------------------------------------------


@router.get("/holidays", response_model=list[HolidayRead])
async def list_holidays(
    year_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    stmt = select(Holiday).order_by(Holiday.date)
    if year_id is not None:
        stmt = stmt.where(Holiday.year_id == year_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post("/holidays", response_model=HolidayRead, status_code=status.HTTP_201_CREATED)
async def create_holiday(
    payload: HolidayWrite,
    principal: AuthPrincipal = Depends(_school_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = Holiday(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/holidays/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holiday(item_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    obj = await _get_or_404(session, Holiday, item_id)
    await session.delete(obj)
    await session.commit()
