"""Student Information System endpoints (Phase 6)."""

from __future__ import annotations

from datetime import date
from typing import Optional

import csv
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.models.parent import Student
from app.models.sis import Admission, AdmissionStage, StudentDocument, StudentStatus
from app.schemas.sis import (
    AdmissionRead,
    AdmissionStageUpdate,
    AdmissionWrite,
    PromotionRequest,
    PromotionResult,
    SiblingLinkRequest,
    StudentCreate,
    StudentDetail,
    StudentDocumentRead,
    StudentDocumentWrite,
    StudentListPage,
    StudentRead,
    StudentUpdate,
    TransferCertificate,
    WithdrawRequest,
)
from app.services.sis import (
    admit_from_admission,
    admit_student,
    create_admission,
    link_siblings,
    list_admissions,
    list_siblings,
    promote,
    search_students,
    update_student,
    withdraw,
)


_school_staff_read = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher", "office_staff",
)
_school_admin = require_roles(
    "school_admin", "principal", "vice_principal", "office_staff"
)


router = APIRouter(
    prefix="/school-admin/students",
    tags=["school-admin"],
    dependencies=[Depends(_school_staff_read)],
)
admissions_router = APIRouter(
    prefix="/school-admin/admissions",
    tags=["school-admin"],
    dependencies=[Depends(_school_admin)],
)


async def _get_student(session: AsyncSession, student_id: int) -> Student:
    student = (await session.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


def _detail_payload(student: Student, sibling_ids: list[int], documents: list[StudentDocument]) -> StudentDetail:
    base = StudentRead.model_validate(student).model_dump()
    return StudentDetail(
        **base,
        documents=[StudentDocumentRead.model_validate(d) for d in documents],
        sibling_ids=sibling_ids,
    )


# ---- Search + listing ------------------------------------------------------


@router.get("", response_model=StudentListPage)
async def list_students(
    q: Optional[str] = Query(default=None, max_length=100),
    class_def_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status_filter: Optional[StudentStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rows, total = await search_students(
        session,
        q=q,
        class_def_id=class_def_id,
        section_id=section_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return StudentListPage(items=[StudentRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/{student_id}", response_model=StudentDetail)
async def get_student(student_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    student = await _get_student(session, student_id)
    siblings = await list_siblings(session, student)
    docs = list(
        (
            await session.execute(
                select(StudentDocument).where(StudentDocument.student_id == student.id)
            )
        ).scalars().all()
    )
    return _detail_payload(student, [s.id for s in siblings], docs)


# ---- Mutations -------------------------------------------------------------


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await admit_student(session, principal.tenant_id, payload)
    return student


@router.patch("/{student_id}", response_model=StudentRead)
async def patch_student(
    student_id: int,
    payload: StudentUpdate,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await _get_student(session, student_id)
    return await update_student(session, student, payload)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Hard-delete a student row.

    Cascading FKs handle the obvious children (documents, parent links).
    For history-bearing records — attendance, fees, exam marks — the
    admin should typically /withdraw instead. We keep DELETE for the
    case where the row was a data-entry mistake and was never used."""
    student = await _get_student(session, student_id)
    await session.delete(student)
    await session.commit()


@router.post("/{student_id}/withdraw", response_model=StudentRead)
async def withdraw_student(
    student_id: int,
    payload: WithdrawRequest,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await _get_student(session, student_id)
    return await withdraw(session, student, payload)


@router.get("/{student_id}/transfer-certificate", response_model=TransferCertificate)
async def transfer_certificate(
    student_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await _get_student(session, student_id)
    return TransferCertificate(
        student=StudentRead.model_validate(student),
        issued_on=date.today(),
        school_name=principal.tenant.school_name,
        school_subdomain=principal.tenant.subdomain,
        last_class_label=student.current_class_label,
        reason=student.remarks,
    )


class BulkImportRow(BaseModel):
    row: int
    admission_number: str | None = None
    full_name: str | None = None
    error: str


class BulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[BulkImportRow]


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_students_route(
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Bulk-admit students from a CSV. Columns (header row required):

    full_name (required), first_name, last_name, date_of_birth (YYYY-MM-DD),
    gender, blood_group, admission_number (optional, auto-generated when
    blank), roll_no, class_def_id, section_id, address, phone, email,
    father_name, mother_name, parent_phone, parent_email.

    Returns per-row results so the admin can fix the failing rows and
    re-upload only those — successful rows aren't reverted."""
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a .csv file",
        )
    raw = (await file.read()).decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    errors: list[BulkImportRow] = []
    imported = 0
    skipped = 0
    log = logging.getLogger(__name__)
    for idx, row in enumerate(reader, start=2):  # row 1 is the header
        full_name = (row.get("full_name") or "").strip()
        if not full_name:
            skipped += 1
            errors.append(BulkImportRow(
                row=idx, error="full_name is required",
            ))
            continue
        try:
            payload = StudentCreate(
                full_name=full_name,
                first_name=(row.get("first_name") or "").strip() or None,
                last_name=(row.get("last_name") or "").strip() or None,
                date_of_birth=(row.get("date_of_birth") or "").strip() or None,
                gender=(row.get("gender") or "").strip() or None,
                blood_group=(row.get("blood_group") or "").strip() or None,
                admission_number=(row.get("admission_number") or "").strip() or None,
                roll_no=(row.get("roll_no") or "").strip() or None,
                class_def_id=int(row["class_def_id"]) if row.get("class_def_id") else None,
                section_id=int(row["section_id"]) if row.get("section_id") else None,
                address=(row.get("address") or "").strip() or None,
                phone=(row.get("phone") or "").strip() or None,
                email=(row.get("email") or "").strip() or None,
                father_name=(row.get("father_name") or "").strip() or None,
                mother_name=(row.get("mother_name") or "").strip() or None,
                parent_phone=(row.get("parent_phone") or "").strip() or None,
                parent_email=(row.get("parent_email") or "").strip() or None,
            )
            await admit_student(session, principal.tenant_id, payload)
            imported += 1
        except HTTPException as e:
            skipped += 1
            errors.append(BulkImportRow(
                row=idx, admission_number=row.get("admission_number"),
                full_name=full_name, error=str(e.detail),
            ))
        except Exception as e:
            log.exception("bulk-import row %s failed", idx)
            skipped += 1
            errors.append(BulkImportRow(
                row=idx, admission_number=row.get("admission_number"),
                full_name=full_name, error=str(e)[:200],
            ))
    return BulkImportResult(imported=imported, skipped=skipped, errors=errors)


@router.post("/promote", response_model=PromotionResult)
async def bulk_promote(
    payload: PromotionRequest,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await promote(session, payload)


# ---- Documents -------------------------------------------------------------


@router.get("/{student_id}/documents", response_model=list[StudentDocumentRead])
async def list_documents(
    student_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await _get_student(session, student_id)
    return list(
        (
            await session.execute(
                select(StudentDocument).where(StudentDocument.student_id == student_id)
            )
        ).scalars().all()
    )


@router.post(
    "/{student_id}/documents",
    response_model=StudentDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_document(
    student_id: int,
    payload: StudentDocumentWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await _get_student(session, student_id)
    doc = StudentDocument(
        tenant_id=principal.tenant_id,
        student_id=student.id,
        kind=payload.kind,
        label=payload.label,
        path=payload.path,
        notes=payload.notes,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


@router.post("/{student_id}/documents/{doc_id}/verify", response_model=StudentDocumentRead)
async def verify_document(
    student_id: int,
    doc_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    doc = (
        await session.execute(
            select(StudentDocument).where(
                StudentDocument.id == doc_id, StudentDocument.student_id == student_id
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    doc.is_verified = True
    await session.commit()
    await session.refresh(doc)
    return doc


@router.delete("/{student_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    student_id: int,
    doc_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    doc = (
        await session.execute(
            select(StudentDocument).where(
                StudentDocument.id == doc_id, StudentDocument.student_id == student_id
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await session.delete(doc)
    await session.commit()


# ---- Siblings --------------------------------------------------------------


@router.post("/link-siblings")
async def link_siblings_route(
    payload: SiblingLinkRequest,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    group = await link_siblings(session, principal.tenant_id, payload.student_ids)
    return {"sibling_group_id": group, "linked_ids": payload.student_ids}


# ---- Admissions funnel -----------------------------------------------------


@admissions_router.get("", response_model=list[AdmissionRead])
async def list_admissions_route(
    stage: Optional[AdmissionStage] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_admissions(session, stage=stage)


@admissions_router.post("", response_model=AdmissionRead, status_code=status.HTTP_201_CREATED)
async def create_admission_route(
    payload: AdmissionWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_admission(session, principal.tenant_id, payload)


@admissions_router.patch("/{admission_id}", response_model=AdmissionRead)
async def update_admission_stage(
    admission_id: int,
    payload: AdmissionStageUpdate,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = (
        await session.execute(select(Admission).where(Admission.id == admission_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
    obj.stage = payload.stage.value
    await session.commit()
    await session.refresh(obj)
    return obj


@admissions_router.post("/{admission_id}/admit", response_model=StudentRead)
async def admit_admission(
    admission_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj = (
        await session.execute(select(Admission).where(Admission.id == admission_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
    if obj.student_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already admitted")
    return await admit_from_admission(session, principal.tenant_id, obj)
