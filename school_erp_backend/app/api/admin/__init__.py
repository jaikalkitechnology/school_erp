"""Super-admin (Jaikalki) APIs. Phase 3 fills these out."""

from fastapi import APIRouter

router = APIRouter(prefix="/admin")


@router.get("/ping", tags=["admin"])
async def ping():
    return {"ok": True, "scope": "super-admin"}
