"""Shared response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    database: str
    redis: str
    uploads_dir: str
    timestamp: datetime


class UploadResponse(BaseModel):
    path: str
    size_bytes: int
    tenant_id: int
    category: str
    subcategory: str


class ErrorResponse(BaseModel):
    detail: str
    request_id: Optional[str] = None
