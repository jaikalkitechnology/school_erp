"""File upload + protected file-serving endpoints.

Phase 1: tenant context comes from the resolved subdomain / X-Tenant-Id header
(via TenantMiddleware). Storage limit is enforced *before* the file hits disk.
Phase 2 will swap the dev override path for JWT-derived tenant_id.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_deps import AuthPrincipal, get_current_principal
from app.core.file_storage import ensure_tenant_dirs, save_upload
from app.core.tenant import TenantContext, require_tenant
from app.core.tenant_session import platform_session
from app.schemas.common import UploadResponse
from app.services.tenants import assert_storage_room

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
    subcategory: str = Form(...),
    ctx: TenantContext = Depends(require_tenant),
    session: AsyncSession = Depends(platform_session),
) -> UploadResponse:
    # Read once to know the size; save_upload will re-validate + optimize.
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )
    await assert_storage_room(session, ctx.tenant_id, len(content))

    # Re-wrap so save_upload's await upload.read() returns the bytes again.
    file.file.seek(0)
    ensure_tenant_dirs(ctx.tenant_id)
    rel, size = await save_upload(file, ctx.tenant_id, category, subcategory)
    return UploadResponse(
        path=rel, size_bytes=size, tenant_id=ctx.tenant_id, category=category, subcategory=subcategory
    )


@router.get("/{file_path:path}")
async def serve_file(
    file_path: str,
    principal: AuthPrincipal = Depends(get_current_principal),
):
    """Authenticated file download.

    We deliberately derive the tenant from the JWT (via get_current_principal)
    rather than from the TenantMiddleware's request.state.tenant. The middleware
    extracts a subdomain from the Host header — on shared hosts like
    api.campus.jaikalki.in the resolved subdomain is "api" which doesn't match
    any school, and the middleware short-circuits with 400 before this handler
    ever runs. JWT-derived tenant is robust to that, still tenant-scoped, and
    still requires a valid bearer token to view anything.
    """
    tenant_id = principal.tenant_id
    base = Path(settings.UPLOAD_DIR).resolve() / f"tenant_{tenant_id}"
    # POST /v1/uploads returns paths like "tenant_1/homework/submissions/abc.jpg"
    # (relative to UPLOAD_DIR). Clients echo that exact string back here, so
    # strip the redundant tenant prefix before re-joining with `base`.
    prefix = f"tenant_{tenant_id}/"
    rel = file_path[len(prefix):] if file_path.startswith(prefix) else file_path
    target = (base / rel).resolve()
    if not str(target).startswith(str(base) + "/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )
    return FileResponse(target)
