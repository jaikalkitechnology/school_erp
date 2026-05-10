"""File upload + protected file-serving endpoints.

Phase 0 ships an unauthenticated stub guarded by ``X-Tenant-Subdomain`` /
``X-Tenant-Id`` so we can manually validate per-tenant isolation. Real auth +
tenant lookup is wired in Phase 2.
"""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.core.file_storage import ensure_tenant_dirs, save_upload
from app.schemas.common import UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _resolve_tenant_id(request: Request) -> int:
    # Phase 1 will plug in subdomain -> tenant_id resolution from DB.
    raw = request.headers.get("x-tenant-id")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header required (Phase 0 stub; replaced by JWT in Phase 2)",
        )
    try:
        tenant_id = int(raw)
        if tenant_id <= 0:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Tenant-Id")
    return tenant_id


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form(...),
    subcategory: str = Form(...),
) -> UploadResponse:
    tenant_id = _resolve_tenant_id(request)
    ensure_tenant_dirs(tenant_id)
    rel, size = await save_upload(file, tenant_id, category, subcategory)
    return UploadResponse(
        path=rel, size_bytes=size, tenant_id=tenant_id, category=category, subcategory=subcategory
    )


@router.get("/{tenant_id}/{file_path:path}")
async def serve_file(request: Request, tenant_id: int, file_path: str):
    caller = _resolve_tenant_id(request)
    if caller != tenant_id:
        # Strict isolation: never serve another tenant's file, regardless of how the URL was constructed.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    base = Path(settings.UPLOAD_DIR).resolve() / f"tenant_{tenant_id}"
    target = (base / file_path).resolve()
    if not str(target).startswith(str(base) + "/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(target)
