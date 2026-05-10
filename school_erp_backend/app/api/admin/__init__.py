"""Super-admin (Jaikalki) APIs."""

from fastapi import APIRouter

from app.api.admin.tenants import (
    extras_router,
    plans_router,
    router as tenants_router,
)

router = APIRouter(prefix="/admin")
router.include_router(tenants_router)
router.include_router(plans_router)
router.include_router(extras_router)


@router.get("/ping", tags=["super-admin"])
async def ping():
    return {"ok": True, "scope": "super-admin"}
