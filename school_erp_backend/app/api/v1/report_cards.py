"""Report card endpoints (Phase 16)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.parent import Parent, ParentChildMapping
from app.models.report_cards import ReportCard, ReportCardStatus
from app.schemas.report_cards import (
    CoCurricularRead,
    CoCurricularWrite,
    GenerateRequest,
    GenerateResult,
    ParentReportCardRow,
    ParentReportCards,
    RemarkRead,
    RemarkWrite,
    ReportCardRead,
    TemplateRead,
    TemplateWrite,
)
from app.services.report_cards import (
    delete_template,
    generate,
    get_card,
    list_co_curricular,
    list_for_section,
    list_remarks,
    list_templates,
    parent_child_cards,
    publish_section,
    upsert_co_curricular,
    upsert_remark,
    upsert_template,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_teacher = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/report-cards",
    tags=["school-admin"],
    dependencies=[Depends(_teacher)],
)


# ---- Templates -------------------------------------------------------------


@router.get("/templates", response_model=list[TemplateRead])
async def list_templates_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_templates(session)


@router.put("/templates", response_model=TemplateRead)
async def upsert_template_route(
    payload: TemplateWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_template(session, principal.tenant_id, payload)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_route(
    template_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await delete_template(session, template_id)


# ---- Co-curricular + remarks ----------------------------------------------


@router.get("/{exam_id}/co-curricular", response_model=list[CoCurricularRead])
async def list_co_curricular_route(
    exam_id: int,
    section_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_co_curricular(session, exam_id, section_id)


@router.post("/{exam_id}/co-curricular", response_model=CoCurricularRead)
async def upsert_co_curricular_route(
    exam_id: int,
    payload: CoCurricularWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_co_curricular(session, principal.tenant_id, exam_id, payload)


@router.get("/{exam_id}/remarks", response_model=list[RemarkRead])
async def list_remarks_route(
    exam_id: int,
    section_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_remarks(session, exam_id, section_id)


@router.post("/{exam_id}/remarks", response_model=RemarkRead)
async def upsert_remark_route(
    exam_id: int,
    payload: RemarkWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_remark(session, principal.tenant_id, exam_id, payload)


# ---- Generation + listing -------------------------------------------------


@router.post("/generate", response_model=GenerateResult)
async def generate_route(
    payload: GenerateRequest,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await generate(session, principal.tenant_id, payload)


@router.post("/{exam_id}/sections/{section_id}/publish")
async def publish_section_route(
    exam_id: int,
    section_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    n = await publish_section(session, exam_id, section_id)
    return {"published": n}


@router.get(
    "/{exam_id}/sections/{section_id}", response_model=list[ReportCardRead]
)
async def list_for_section_route(
    exam_id: int,
    section_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_for_section(session, exam_id, section_id)


@router.get("/{card_id}/pdf")
async def download_pdf_route(
    card_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rc = await get_card(session, card_id)
    if not rc.pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not generated")
    target = (Path(settings.UPLOAD_DIR) / rc.pdf_path).resolve()
    base = Path(settings.UPLOAD_DIR).resolve()
    if not str(target).startswith(str(base) + "/") or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF missing")
    return FileResponse(target, media_type="application/pdf", filename=f"report_card_{rc.id}.pdf")


# ---- Parent view -----------------------------------------------------------


parent_router = APIRouter(
    prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)]
)


def _parent_url(card_id: int) -> str:
    return f"/v1/parent/report-cards/{card_id}/pdf"


@parent_router.get(
    "/children/{student_id}/report-cards",
    response_model=ParentReportCards,
)
async def parent_cards_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")

    cards = await parent_child_cards(session, student_id)
    rows: list[ParentReportCardRow] = []
    for rc in cards:
        snap = rc.snapshot or {}
        rows.append(
            ParentReportCardRow(
                report_card_id=rc.id,
                exam_id=rc.exam_id,
                exam_name=snap.get("exam_name", ""),
                status=ReportCardStatus(rc.status),
                percentage=rc.percentage,
                overall_grade=rc.overall_grade,
                rank_in_section=rc.rank_in_section,
                pdf_url=_parent_url(rc.id),
                published_at=rc.published_at,
            )
        )
    return ParentReportCards(student_id=student_id, rows=rows)


@parent_router.get("/report-cards/{card_id}/pdf")
async def parent_download_route(
    card_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    rc = (
        await session.execute(select(ReportCard).where(ReportCard.id == card_id))
    ).scalar_one_or_none()
    if rc is None or rc.status != ReportCardStatus.PUBLISHED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report card not available")
    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == rc.student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    target = (Path(settings.UPLOAD_DIR) / (rc.pdf_path or "")).resolve()
    base = Path(settings.UPLOAD_DIR).resolve()
    if not rc.pdf_path or not str(target).startswith(str(base) + "/") or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF missing")
    return FileResponse(target, media_type="application/pdf", filename=f"report_card_{rc.id}.pdf")
