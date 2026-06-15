"""Local-disk file storage with strict per-tenant isolation.

Layout:
    uploads/
        tenant_1/
            students/photos/
            students/documents/
            teachers/photos/
            ...
        tenant_2/
            ...

Why this exists in Phase 0:
    The file-serving endpoint is auth-gated in Phase 2. Right now we just
    materialize the directory tree and expose helpers callers will use later.
"""

from __future__ import annotations

import io
import secrets
import uuid
from pathlib import Path
from typing import Iterable, Tuple

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.config import settings

# Canonical sub-tree every tenant gets. Keep flat — deep nesting is annoying to back up.
TENANT_SUBDIRS: tuple[str, ...] = (
    "students/photos",
    "students/documents",
    "teachers/photos",
    "teachers/documents",
    "exams/question_papers",
    "homework/assignments",
    "homework/submissions",
    "fees/receipts",
    "reports/report_cards",
    "library/book_covers",
    "branding",
)

ALLOWED_EXTENSIONS_BY_CATEGORY: dict[str, set[str]] = {
    "photos": {".jpg", ".jpeg", ".png"},
    "documents": {".pdf", ".docx", ".jpg", ".jpeg", ".png"},
    "reports": {".pdf"},
    "attachments": {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"},
    "branding": {".png", ".jpg", ".jpeg", ".svg"},
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _base_dir() -> Path:
    base = Path(settings.UPLOAD_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base


def setup_upload_directory() -> None:
    """Create top-level uploads/ and a .gitkeep so the dir survives in git."""
    base = _base_dir()
    gitkeep = base / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def ensure_tenant_dirs(tenant_id: int) -> Path:
    """Create the full per-tenant subtree, returning the tenant root path."""
    if tenant_id <= 0:
        raise ValueError("tenant_id must be a positive integer")
    root = _base_dir() / f"tenant_{tenant_id}"
    for sub in TENANT_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _resolve_safe(tenant_id: int, *parts: str) -> Path:
    """Resolve a path inside a tenant root, blocking traversal attempts."""
    root = (_base_dir() / f"tenant_{tenant_id}").resolve()
    target = (root.joinpath(*parts)).resolve()
    if not str(target).startswith(str(root) + "/") and target != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return target


def _check_extension(filename: str, allowed: Iterable[str]) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {ext or '(none)'} not allowed",
        )
    return ext


def _optimize_image(content: bytes, ext: str) -> bytes:
    if ext not in IMAGE_EXTENSIONS:
        return content
    with Image.open(io.BytesIO(content)) as img:
        img = img.convert("RGB") if ext in {".jpg", ".jpeg"} else img
        if img.width > settings.MAX_IMAGE_WIDTH:
            ratio = settings.MAX_IMAGE_WIDTH / img.width
            new_size = (settings.MAX_IMAGE_WIDTH, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        out = io.BytesIO()
        fmt = "JPEG" if ext in {".jpg", ".jpeg"} else "PNG"
        img.save(out, format=fmt, optimize=True, quality=85 if fmt == "JPEG" else None)
        return out.getvalue()


async def save_upload(
    upload: UploadFile,
    tenant_id: int,
    category: str,
    subcategory: str,
) -> Tuple[str, int]:
    """Validate, optimize, and persist an upload. Returns (relative_path, size_bytes)."""
    allowed = ALLOWED_EXTENSIONS_BY_CATEGORY.get(subcategory) or ALLOWED_EXTENSIONS_BY_CATEGORY["attachments"]
    ext = _check_extension(upload.filename or "", allowed)

    content = await upload.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    content = _optimize_image(content, ext)

    ensure_tenant_dirs(tenant_id)
    filename = f"{uuid.uuid4().hex}{secrets.token_hex(2)}{ext}"
    target = _resolve_safe(tenant_id, category, subcategory, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    # _resolve_safe(.resolve()) gave us an absolute target; _base_dir()
    # is whatever settings.UPLOAD_DIR holds (often relative like
    # "uploads"). relative_to() can't compare across that mix, so
    # resolve the base too before subtracting.
    rel = target.relative_to(_base_dir().resolve())
    return str(rel), len(content)


def get_tenant_storage_used_mb(tenant_id: int) -> float:
    root = _base_dir() / f"tenant_{tenant_id}"
    if not root.exists():
        return 0.0
    total = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    return total / (1024 * 1024)
