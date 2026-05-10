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
async def serve_file(file_path: str, ctx: TenantContext = Depends(require_tenant)):
    base = Path(settings.UPLOAD_DIR).resolve() / f"tenant_{ctx.tenant_id}"
    target = (base / file_path).resolve()
    if not str(target).startswith(str(base) + "/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(target)
