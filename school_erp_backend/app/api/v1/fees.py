"""Fee management endpoints (Phase 11)."""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.fees import FeeInvoice, FeePayment
from app.models.parent import ParentChildMapping
from app.schemas.fees import (
    CollectPaymentRequest,
    CollectionSummary,
    ConfirmPaymentRequest,
    DefaulterRow,
    FeeCategoryRead,
    FeeCategoryWrite,
    FeeDiscountRead,
    FeeDiscountWrite,
    FeeInvoiceRead,
    FeePaymentRead,
    FeeStructureRead,
    FeeStructureWrite,
    GenerateInvoicesRequest,
    GenerateInvoicesResult,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    ReceiptPayload,
    StudentFeeView,
)
from app.services.fees import (
    collect_payment,
    collection_summary,
    confirm_online_payment,
    create_category,
    create_structure,
    deactivate_discount,
    defaulters,
    generate_invoices,
    initiate_online_payment,
    list_categories,
    list_structures,
    list_student_fees,
    receipt_payload,
    update_category,
    update_structure,
    upsert_discount,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_accountant = require_roles("school_admin", "principal", "vice_principal", "accountant")
_school_view = require_roles(
    "school_admin", "principal", "vice_principal", "accountant",
    "office_staff", "coordinator", "class_teacher",
)


router = APIRouter(
    prefix="/school-admin/fees",
    tags=["school-admin"],
    dependencies=[Depends(_school_view)],
)


# ---- Categories ------------------------------------------------------------


@router.get("/categories", response_model=list[FeeCategoryRead])
async def list_categories_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_categories(session)


@router.post("/categories", response_model=FeeCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category_route(
    payload: FeeCategoryWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_category(session, principal.tenant_id, payload)


@router.patch("/categories/{category_id}", response_model=FeeCategoryRead)
async def update_category_route(
    category_id: int,
    payload: FeeCategoryWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_category(session, category_id, payload)


# ---- Structures ------------------------------------------------------------


@router.get("/structures", response_model=list[FeeStructureRead])
async def list_structures_route(
    class_def_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_structures(session, class_def_id=class_def_id)


@router.post("/structures", response_model=FeeStructureRead, status_code=status.HTTP_201_CREATED)
async def create_structure_route(
    payload: FeeStructureWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_structure(session, principal.tenant_id, payload)


@router.patch("/structures/{structure_id}", response_model=FeeStructureRead)
async def update_structure_route(
    structure_id: int,
    payload: FeeStructureWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_structure(session, structure_id, payload)


@router.post(
    "/structures/{structure_id}/generate", response_model=GenerateInvoicesResult,
)
async def generate_invoices_route(
    structure_id: int,
    payload: GenerateInvoicesRequest,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await generate_invoices(session, principal.tenant_id, structure_id, payload)


# ---- Discounts -------------------------------------------------------------


@router.post("/discounts", response_model=FeeDiscountRead, status_code=status.HTTP_201_CREATED)
async def create_discount_route(
    payload: FeeDiscountWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_discount(session, principal.tenant_id, payload)


@router.delete("/discounts/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_discount_route(
    discount_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await deactivate_discount(session, discount_id)


# ---- Per-student view + collection ----------------------------------------


@router.get("/students/{student_id}", response_model=StudentFeeView)
async def student_fees(
    student_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_student_fees(session, student_id)


@router.post("/collect", response_model=FeePaymentRead, status_code=status.HTTP_201_CREATED)
async def collect_route(
    payload: CollectPaymentRequest,
    principal: AuthPrincipal = Depends(_accountant),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await collect_payment(session, principal.tenant_id, principal.user_id, payload)


@router.get("/payments/{payment_id}/receipt", response_model=ReceiptPayload)
async def receipt_route(
    payment_id: int,
    principal: AuthPrincipal = Depends(_accountant),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await receipt_payload(
        session,
        school_name=principal.tenant.school_name,
        school_subdomain=principal.tenant.subdomain,
        payment_id=payment_id,
    )


# ---- Reports ----------------------------------------------------------------


@router.get("/reports/collection", response_model=CollectionSummary)
async def collection_route(
    start: _date,
    end: _date,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await collection_summary(session, start=start, end=end)


@router.get("/reports/defaulters", response_model=list[DefaulterRow])
async def defaulters_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await defaulters(session)


# ---- Parent-facing -------------------------------------------------------


parent_router = APIRouter(prefix="/parent", tags=["parent"])
_parent_role = require_roles("parent")


async def _ensure_linked_to_parent(
    session: AsyncSession, *, user_id: int, student_id: int
) -> None:
    from app.models.parent import Parent

    parent = (
        await session.execute(
            select(Parent).where(Parent.user_id == user_id)
        )
    ).scalar_one_or_none()
    if parent is None:
        raise from_403("Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise from_403("Child not linked")


def from_403(detail: str):
    from fastapi import HTTPException

    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


@parent_router.get(
    "/children/{student_id}/fees",
    response_model=StudentFeeView,
    dependencies=[Depends(_parent_role)],
)
async def parent_child_fees(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    await _ensure_linked_to_parent(session, user_id=principal.user_id, student_id=student_id)
    return await list_student_fees(session, student_id)


@parent_router.post(
    "/payments/initiate",
    response_model=InitiatePaymentResponse,
    dependencies=[Depends(_parent_role)],
)
async def parent_initiate_payment(
    payload: InitiatePaymentRequest,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    invoice = (
        await session.execute(select(FeeInvoice).where(FeeInvoice.id == payload.invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise from_403("Invoice not found")
    await _ensure_linked_to_parent(
        session, user_id=principal.user_id, student_id=invoice.student_id
    )
    return await initiate_online_payment(session, principal.tenant_id, principal.user_id, payload)


@parent_router.post(
    "/payments/confirm",
    response_model=FeePaymentRead,
    dependencies=[Depends(_parent_role)],
)
async def parent_confirm_payment(
    payload: ConfirmPaymentRequest,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await confirm_online_payment(session, payload)
