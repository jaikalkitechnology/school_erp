"""Report card service (Phase 16).

Generates per-student cards by reusing the Phase 15 ``section_results`` aggregator,
augments them with co-curricular grades + remarks, persists a ``snapshot`` JSON
plus a rendered PDF on disk, and exposes parent-side download.
"""

from __future__ import annotations

import io
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_storage import ensure_tenant_dirs
from app.models.academic import ClassDef, Section, Subject
from app.models.exams import Exam
from app.models.parent import Student
from app.models.report_cards import (
    CoCurricularGrade,
    ReportCard,
    ReportCardRemark,
    ReportCardStatus,
    ReportCardTemplate,
)
from app.models.tenant import Tenant
from app.schemas.report_cards import (
    CoCurricularWrite,
    GenerateRequest,
    GenerateResult,
    RemarkWrite,
    TemplateWrite,
)
from app.services.exams import section_results


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Templates -------------------------------------------------------------


async def list_templates(session: AsyncSession) -> list[ReportCardTemplate]:
    return list(
        (
            await session.execute(
                select(ReportCardTemplate).order_by(ReportCardTemplate.id.desc())
            )
        ).scalars().all()
    )


async def upsert_template(
    session: AsyncSession, tenant_id: int, payload: TemplateWrite
) -> ReportCardTemplate:
    obj = (
        await session.execute(
            select(ReportCardTemplate).where(ReportCardTemplate.code == payload.code)
        )
    ).scalar_one_or_none()
    if obj is None:
        obj = ReportCardTemplate(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            board=payload.board.value,
            layout=payload.layout,
            is_default=payload.is_default,
        )
        session.add(obj)
    else:
        obj.name = payload.name
        obj.board = payload.board.value
        obj.layout = payload.layout
        obj.is_default = payload.is_default

    if obj.is_default:
        await session.execute(
            ReportCardTemplate.__table__.update()
            .where(ReportCardTemplate.code != obj.code)
            .values(is_default=False)
        )
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_template(session: AsyncSession, template_id: int) -> None:
    obj = (
        await session.execute(
            select(ReportCardTemplate).where(ReportCardTemplate.id == template_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await session.delete(obj)
    await session.commit()


async def _default_template(session: AsyncSession) -> Optional[ReportCardTemplate]:
    return (
        await session.execute(
            select(ReportCardTemplate)
            .where(ReportCardTemplate.is_default.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()


# ---- Co-curricular + remarks ----------------------------------------------


async def list_co_curricular(
    session: AsyncSession, exam_id: int, section_id: int
) -> list[CoCurricularGrade]:
    student_ids = list(
        (
            await session.execute(
                select(Student.id).where(Student.section_id == section_id)
            )
        ).scalars().all()
    )
    if not student_ids:
        return []
    return list(
        (
            await session.execute(
                select(CoCurricularGrade).where(
                    CoCurricularGrade.exam_id == exam_id,
                    CoCurricularGrade.student_id.in_(student_ids),
                )
            )
        ).scalars().all()
    )


async def upsert_co_curricular(
    session: AsyncSession,
    tenant_id: int,
    exam_id: int,
    payload: CoCurricularWrite,
) -> CoCurricularGrade:
    obj = (
        await session.execute(
            select(CoCurricularGrade).where(
                CoCurricularGrade.exam_id == exam_id,
                CoCurricularGrade.student_id == payload.student_id,
                CoCurricularGrade.area == payload.area,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        obj = CoCurricularGrade(
            tenant_id=tenant_id,
            exam_id=exam_id,
            student_id=payload.student_id,
            area=payload.area,
            grade=payload.grade,
            remarks=payload.remarks,
        )
        session.add(obj)
    else:
        obj.grade = payload.grade
        obj.remarks = payload.remarks
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_remarks(
    session: AsyncSession, exam_id: int, section_id: int
) -> list[ReportCardRemark]:
    student_ids = list(
        (
            await session.execute(
                select(Student.id).where(Student.section_id == section_id)
            )
        ).scalars().all()
    )
    if not student_ids:
        return []
    return list(
        (
            await session.execute(
                select(ReportCardRemark).where(
                    ReportCardRemark.exam_id == exam_id,
                    ReportCardRemark.student_id.in_(student_ids),
                )
            )
        ).scalars().all()
    )


async def upsert_remark(
    session: AsyncSession,
    tenant_id: int,
    exam_id: int,
    payload: RemarkWrite,
) -> ReportCardRemark:
    obj = (
        await session.execute(
            select(ReportCardRemark).where(
                ReportCardRemark.exam_id == exam_id,
                ReportCardRemark.student_id == payload.student_id,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        obj = ReportCardRemark(
            tenant_id=tenant_id,
            exam_id=exam_id,
            student_id=payload.student_id,
            teacher_remark=payload.teacher_remark,
            principal_remark=payload.principal_remark,
        )
        session.add(obj)
    else:
        obj.teacher_remark = payload.teacher_remark
        obj.principal_remark = payload.principal_remark
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Generation ------------------------------------------------------------


def _render_pdf(snapshot: dict, tenant_id: int) -> str:
    """Render a snapshot to PDF on disk under the tenant's reports folder.
    Returns the relative path inside ``settings.UPLOAD_DIR``."""

    ensure_tenant_dirs(tenant_id)
    base = Path(settings.UPLOAD_DIR) / f"tenant_{tenant_id}" / "reports" / "report_cards"
    base.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{secrets.token_hex(2)}.pdf"
    target = base / filename

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    story: list = []

    school = snapshot.get("school", {})
    story.append(Paragraph(f"<b>{school.get('name', 'School')}</b>", styles["Title"]))
    if school.get("address"):
        story.append(Paragraph(school["address"], styles["Normal"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Report Card — {snapshot.get('exam_name', '')}</b>", styles["Heading2"],
    ))
    story.append(Spacer(1, 6))

    student = snapshot.get("student", {})
    student_table = Table(
        [
            ["Name", student.get("full_name", ""), "Adm. No.", student.get("admission_number", "")],
            ["Class", student.get("class_label", ""), "Section", student.get("section_name", "")],
        ],
        colWidths=[25 * mm, 65 * mm, 25 * mm, 55 * mm],
    )
    student_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FFF7E6")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#FFF7E6")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 10))

    # Subjects.
    rows = [["Subject", "Max", "Obtained", "Grade", "Status"]]
    for s in snapshot.get("subjects", []):
        rows.append([
            s.get("subject_name", ""),
            str(s.get("max_marks", "")),
            "" if s.get("obtained") is None else str(s["obtained"]),
            s.get("grade") or "-",
            s.get("status", ""),
        ])
    rows.append([
        "Total",
        str(snapshot.get("total_max", "")),
        str(snapshot.get("total_obtained", "")),
        snapshot.get("overall_grade") or "-",
        snapshot.get("overall_status", ""),
    ])
    subj_table = Table(rows, colWidths=[70 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm])
    subj_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F1248")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFE4B8")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(subj_table)
    story.append(Spacer(1, 8))

    # Summary stats.
    story.append(Paragraph(
        f"<b>Percentage:</b> {snapshot.get('percentage', 0)}%   "
        f"<b>Rank:</b> {snapshot.get('rank_in_section', '-')}",
        styles["Normal"],
    ))

    co = snapshot.get("co_curricular", [])
    if co:
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>Co-curricular</b>", styles["Heading4"]))
        co_rows = [["Area", "Grade", "Remarks"]]
        for c in co:
            co_rows.append([c.get("area", ""), c.get("grade", ""), c.get("remarks") or ""])
        co_table = Table(co_rows, colWidths=[60 * mm, 30 * mm, 80 * mm])
        co_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(co_table)

    rem = snapshot.get("remarks", {})
    if rem.get("teacher_remark") or rem.get("principal_remark"):
        story.append(Spacer(1, 10))
        if rem.get("teacher_remark"):
            story.append(Paragraph(
                f"<b>Class Teacher:</b> {rem['teacher_remark']}", styles["Normal"]
            ))
        if rem.get("principal_remark"):
            story.append(Paragraph(
                f"<b>Principal:</b> {rem['principal_remark']}", styles["Normal"]
            ))

    story.append(Spacer(1, 25))
    sign_table = Table(
        [["__________________", "__________________", "__________________"],
         ["Class Teacher", "Principal", "Parent Signature"]],
        colWidths=[60 * mm, 60 * mm, 60 * mm],
    )
    sign_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sign_table)

    doc.build(story)
    target.write_bytes(buf.getvalue())
    return str(target.relative_to(Path(settings.UPLOAD_DIR)))


async def generate(
    session: AsyncSession,
    tenant_id: int,
    payload: GenerateRequest,
) -> GenerateResult:
    exam = (
        await session.execute(select(Exam).where(Exam.id == payload.exam_id))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    section = (
        await session.execute(select(Section).where(Section.id == payload.section_id))
    ).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    template = None
    if payload.template_id:
        template = (
            await session.execute(
                select(ReportCardTemplate).where(ReportCardTemplate.id == payload.template_id)
            )
        ).scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    if template is None:
        template = await _default_template(session)
    template_id = template.id if template else None

    # Compute results once for the whole section.
    results = await section_results(session, exam_id=exam.id, section_id=section.id)
    if not results.students:
        return GenerateResult(generated=0, skipped=0, skipped_reasons=["No students in section"])

    # Subject name map.
    subj_ids: set[int] = set()
    for sr in results.students:
        for sub in sr.subjects:
            subj_ids.add(sub.subject_id)
    subject_names: dict[int, str] = {}
    if subj_ids:
        subject_names = {
            s.id: s.name
            for s in (
                await session.execute(select(Subject).where(Subject.id.in_(subj_ids)))
            ).scalars().all()
        }

    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    school_block = {
        "name": tenant.school_name if tenant else "School",
        "address": tenant.address if tenant else "",
    }
    class_def = (
        await session.execute(
            select(ClassDef).where(ClassDef.id == section.class_def_id)
        )
    ).scalar_one_or_none()
    class_label = class_def.name if class_def else ""

    # Pre-fetch co-curricular + remarks scoped to this section + exam.
    co_grades = await list_co_curricular(session, exam.id, section.id)
    co_by_student: dict[int, list[dict]] = {}
    for cg in co_grades:
        co_by_student.setdefault(cg.student_id, []).append(
            {"area": cg.area, "grade": cg.grade, "remarks": cg.remarks}
        )
    remark_rows = await list_remarks(session, exam.id, section.id)
    rem_by_student = {
        r.student_id: {
            "teacher_remark": r.teacher_remark,
            "principal_remark": r.principal_remark,
        }
        for r in remark_rows
    }

    existing = {
        rc.student_id: rc
        for rc in (
            await session.execute(
                select(ReportCard).where(
                    ReportCard.exam_id == exam.id,
                    ReportCard.student_id.in_([sr.student_id for sr in results.students]),
                )
            )
        ).scalars().all()
    }

    generated = 0
    skipped = 0
    reasons: list[str] = []
    for sr in results.students:
        snapshot = {
            "school": school_block,
            "exam_id": exam.id,
            "exam_name": exam.name,
            "student": {
                "full_name": sr.full_name,
                "admission_number": sr.admission_number,
                "class_label": class_label,
                "section_name": section.name,
            },
            "subjects": [
                {
                    "subject_id": sub.subject_id,
                    "subject_name": subject_names.get(sub.subject_id, str(sub.subject_id)),
                    "max_marks": str(sub.max_marks),
                    "obtained": str(sub.obtained) if sub.obtained is not None else None,
                    "grade": sub.grade,
                    "status": sub.status.value,
                }
                for sub in sr.subjects
            ],
            "total_max": str(sr.total_max),
            "total_obtained": str(sr.total_obtained),
            "percentage": sr.percentage,
            "overall_grade": sr.overall_grade,
            "overall_status": sr.overall_status.value,
            "rank_in_section": sr.rank_in_section,
            "co_curricular": co_by_student.get(sr.student_id, []),
            "remarks": rem_by_student.get(sr.student_id, {}),
        }
        try:
            pdf_path = _render_pdf(snapshot, tenant_id)
        except Exception as exc:  # pragma: no cover - safety net
            skipped += 1
            reasons.append(f"{sr.full_name}: render failed ({exc})")
            continue

        rc = existing.get(sr.student_id)
        now = _now()
        if rc is None:
            rc = ReportCard(
                tenant_id=tenant_id,
                exam_id=exam.id,
                student_id=sr.student_id,
                template_id=template_id,
                status=(
                    ReportCardStatus.PUBLISHED.value if payload.publish
                    else ReportCardStatus.GENERATED.value
                ),
                total_marks=sr.total_max,
                obtained_marks=sr.total_obtained,
                percentage=Decimal(str(sr.percentage)),
                overall_grade=sr.overall_grade,
                rank_in_section=sr.rank_in_section,
                snapshot=snapshot,
                pdf_path=pdf_path,
                generated_at=now,
                published_at=now if payload.publish else None,
            )
            session.add(rc)
        else:
            rc.template_id = template_id
            rc.status = (
                ReportCardStatus.PUBLISHED.value if payload.publish
                else ReportCardStatus.GENERATED.value
            )
            rc.total_marks = sr.total_max
            rc.obtained_marks = sr.total_obtained
            rc.percentage = Decimal(str(sr.percentage))
            rc.overall_grade = sr.overall_grade
            rc.rank_in_section = sr.rank_in_section
            rc.snapshot = snapshot
            rc.pdf_path = pdf_path
            rc.generated_at = now
            if payload.publish:
                rc.published_at = now
        generated += 1

    await session.commit()
    return GenerateResult(generated=generated, skipped=skipped, skipped_reasons=reasons)


async def publish_section(
    session: AsyncSession, exam_id: int, section_id: int
) -> int:
    student_ids = list(
        (
            await session.execute(
                select(Student.id).where(Student.section_id == section_id)
            )
        ).scalars().all()
    )
    if not student_ids:
        return 0
    rows = list(
        (
            await session.execute(
                select(ReportCard).where(
                    ReportCard.exam_id == exam_id,
                    ReportCard.student_id.in_(student_ids),
                )
            )
        ).scalars().all()
    )
    now = _now()
    for r in rows:
        r.status = ReportCardStatus.PUBLISHED.value
        r.published_at = now
    await session.commit()
    return len(rows)


async def list_for_section(
    session: AsyncSession, exam_id: int, section_id: int
) -> list[ReportCard]:
    student_ids = list(
        (
            await session.execute(
                select(Student.id).where(Student.section_id == section_id)
            )
        ).scalars().all()
    )
    if not student_ids:
        return []
    return list(
        (
            await session.execute(
                select(ReportCard).where(
                    ReportCard.exam_id == exam_id,
                    ReportCard.student_id.in_(student_ids),
                ).order_by(ReportCard.id)
            )
        ).scalars().all()
    )


async def get_card(session: AsyncSession, card_id: int) -> ReportCard:
    rc = (
        await session.execute(select(ReportCard).where(ReportCard.id == card_id))
    ).scalar_one_or_none()
    if rc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report card not found")
    return rc


# ---- Parent view -----------------------------------------------------------


async def parent_child_cards(
    session: AsyncSession, student_id: int
) -> list[ReportCard]:
    return list(
        (
            await session.execute(
                select(ReportCard).where(
                    ReportCard.student_id == student_id,
                    ReportCard.status == ReportCardStatus.PUBLISHED.value,
                ).order_by(ReportCard.id.desc())
            )
        ).scalars().all()
    )
