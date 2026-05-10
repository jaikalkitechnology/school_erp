"""Phase 21 super-admin billing endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_super_admin
from app.core.tenant_session import platform_session
from app.schemas.billing import (
    BillingInvoiceRead,
    BillingPaymentCreate,
    BillingPaymentRead,
    BillingRefundCreate,
    BillingRefundRead,
    BillingReports,
    BulkRenewRequest,
    BulkRenewResult,
    GenerateInvoiceRequest,
    PlanChangeRequest,
    PlanChangeResult,
)
from app.services.billing import (
    auto_renew,
    change_plan,
    generate_invoice,
    get_invoice,
    list_invoices,
    list_payments,
    record_payment,
    record_refund,
    reports,
    void_invoice,
)


router = APIRouter(prefix="/billing", tags=["super-admin"])


@router.get("/invoices", response_model=list[BillingInvoiceRead])
async def list_invoices_route(
    tenant_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await list_invoices(session, tenant_id=tenant_id, status_filter=status_filter)


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceRead)
async def get_invoice_route(
    invoice_id: int,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await get_invoice(session, invoice_id)


@router.post("/invoices", response_model=BillingInvoiceRead, status_code=201)
async def generate_invoice_route(
    payload: GenerateInvoiceRequest,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await generate_invoice(session, payload)


@router.post("/invoices/{invoice_id}/void", response_model=BillingInvoiceRead)
async def void_invoice_route(
    invoice_id: int,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await void_invoice(session, invoice_id)


@router.post("/auto-renew", response_model=BulkRenewResult)
async def auto_renew_route(
    payload: BulkRenewRequest,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await auto_renew(session, payload)


@router.get("/invoices/{invoice_id}/payments", response_model=list[BillingPaymentRead])
async def list_payments_route(
    invoice_id: int,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await list_payments(session, invoice_id)


@router.post("/payments", response_model=BillingPaymentRead, status_code=201)
async def record_payment_route(
    payload: BillingPaymentCreate,
    principal: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await record_payment(session, principal.user_id, payload)


@router.post("/refunds", response_model=BillingRefundRead, status_code=201)
async def record_refund_route(
    payload: BillingRefundCreate,
    principal: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await record_refund(session, principal.user_id, payload)


@router.post("/plan-change", response_model=PlanChangeResult)
async def plan_change_route(
    payload: PlanChangeRequest,
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await change_plan(session, payload)


@router.get("/reports", response_model=BillingReports)
async def reports_route(
    _: AuthPrincipal = Depends(require_super_admin()),
    session: AsyncSession = Depends(platform_session),
):
    return await reports(session)
