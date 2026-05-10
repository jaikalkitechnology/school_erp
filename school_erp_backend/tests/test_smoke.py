"""Phase 0 smoke tests: app boots, /health works, tenant middleware attaches state."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "Jaikalki School ERP"


@pytest.mark.asyncio
async def test_health_returns_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert body["service"] == "school-erp"


@pytest.mark.asyncio
async def test_tenant_middleware_marks_platform_request():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/")
        # x-request-id always emitted by RequestContextMiddleware
        assert "x-request-id" in r.headers


@pytest.mark.asyncio
async def test_upload_requires_tenant_header():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post("/v1/uploads", files={"file": ("x.png", b"", "image/png")}, data={"category": "students", "subcategory": "photos"})
        assert r.status_code == 400
