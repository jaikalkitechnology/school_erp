"""File upload + protected file-serving endpoints.

Both POST + GET derive the tenant from the JWT bearer token (via
``get_current_principal``) rather than the Host-header subdomain. On
the shared production host (api.campus.jaikalki.in) the middleware
extracts "api" as the subdomain — and "api" is in the platform-host
exclusion list, so it falls through to a platform context with
``tenant_id=None``. With JWT-derived tenant, uploads work whether or
not the client sends ``X-Tenant-Subdomain``.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_deps import AuthPrincipal, get_current_principal
from app.core.file_storage import ensure_tenant_dirs, save_upload
from app.core.tenant_session import platform_session
from app.schemas.common import UploadResponse
from app.services.tenants import assert_storage_room


log = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
    subcategory: str = Form(...),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
) -> UploadResponse:
    tenant_id = principal.tenant_id
    try:
        # Read once to know the size; save_upload will re-validate + optimize.
        content = await file.read()
    except Exception as e:
        log.exception("Failed to read upload body")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read upload: {e}",
        )
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )
    try:
        await assert_storage_room(session, tenant_id, len(content))
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Storage limit check failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage limit check failed: {e}",
        )

    # Re-wrap so save_upload's `await upload.read()` returns the bytes again.
    try:
        file.file.seek(0)
    except Exception:
        # Some UploadFile backends don't expose .seek on .file; we already
        # have the content bytes so save_upload will read empty — that's a
        # bug worth surfacing rather than silently saving 0 bytes.
        log.warning("Could not rewind upload; save_upload may see empty body")

    try:
        ensure_tenant_dirs(tenant_id)
    except Exception as e:
        log.exception("ensure_tenant_dirs failed for tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not prepare upload directory: {e}",
        )

    try:
        rel, size = await save_upload(file, tenant_id, category, subcategory)
    except HTTPException:
        # save_upload raises 400 for bad extension / oversize — pass through.
        raise
    except Exception as e:
        log.exception(
            "save_upload failed (category=%s subcategory=%s filename=%s)",
            category, subcategory, file.filename,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not save upload: {e}",
        )
    return UploadResponse(
        path=rel,
        size_bytes=size,
        tenant_id=tenant_id,
        category=category,
        subcategory=subcategory,
    )


@router.get("/{file_path:path}")
async def serve_file(
    file_path: str,
    principal: AuthPrincipal = Depends(get_current_principal),
):
    """Authenticated file download — tenant comes from the JWT."""
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
