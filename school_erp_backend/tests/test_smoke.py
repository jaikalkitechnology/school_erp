"""Phase 0 smoke tests: app boots, /health works, tenant-aware uploads guarded."""

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
async def test_request_id_header_attached():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/")
        assert "x-request-id" in r.headers


@pytest.mark.asyncio
async def test_upload_requires_tenant_context():
    """Without a tenant header / subdomain, upload must reject with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/uploads",
            files={"file": ("x.png", b"", "image/png")},
            data={"category": "students", "subcategory": "photos"},
        )
        assert r.status_code == 400
