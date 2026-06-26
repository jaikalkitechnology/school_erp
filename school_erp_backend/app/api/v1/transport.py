"""Transport endpoints (Phase 18)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.parent import Parent, ParentChildMapping
from app.schemas.transport import (
    AllocationRead,
    AllocationWrite,
    BoardingRead,
    BoardingWrite,
    BusRead,
    BusWrite,
    DriverRead,
    DriverWrite,
    FuelRead,
    FuelWrite,
    GpsPing,
    MaintenanceRead,
    MaintenanceWrite,
    ParentTransport,
    RouteRead,
    RouteWithCounts,
    RouteWrite,
    StopBulk,
    StopRead,
    TripRead,
    TripStart,
    TripView,
)
from app.services.transport import (
    add_fuel,
    add_maintenance,
    complete_trip,
    create_bus,
    create_driver,
    create_route,
    deallocate,
    list_allocations_for_route,
    list_boardings,
    list_buses,
    list_drivers,
    list_fuel,
    list_maintenance,
    list_routes,
    list_stops,
    parent_transport,
    ping_trip,
    record_boarding,
    replace_stops,
    start_trip,
    trip_view,
    update_bus,
    update_driver,
    update_route,
    upsert_allocation,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_transport_staff = require_roles(
    "school_admin", "principal", "vice_principal", "transport_manager", "coordinator",
)
_reader = require_roles(
    "school_admin", "principal", "vice_principal", "transport_manager",
    "coordinator", "class_teacher", "subject_teacher",
)
_driver_or_staff = require_roles(
    # Bus / driver functionality is now gated to the single
    # ``transport_manager`` role. Senior staff (school_admin /
    # principal / vice_principal / coordinator) still manage routes
    # and buses through the admin web — they don't need to start
    # trips or push GPS pings, so they're intentionally left out.
    "transport_manager",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/transport",
    tags=["school-admin"],
    dependencies=[Depends(_reader)],
)


# ---- Buses + drivers ------------------------------------------------------


@router.get("/buses", response_model=list[BusRead])
async def list_buses_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_buses(session)


@router.post("/buses", response_model=BusRead, status_code=status.HTTP_201_CREATED)
async def create_bus_route(
    payload: BusWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_bus(session, principal.tenant_id, payload)


@router.patch("/buses/{bus_id}", response_model=BusRead)
async def update_bus_route(
    bus_id: int,
    payload: BusWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_bus(session, bus_id, payload)


@router.get("/drivers", response_model=list[DriverRead])
async def list_drivers_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_drivers(session)


@router.post("/drivers", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
async def create_driver_route(
    payload: DriverWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_driver(session, principal.tenant_id, payload)


@router.patch("/drivers/{driver_id}", response_model=DriverRead)
async def update_driver_route(
    driver_id: int,
    payload: DriverWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_driver(session, driver_id, payload)


# ---- Routes + stops -------------------------------------------------------


@router.get("/routes", response_model=list[RouteWithCounts])
async def list_routes_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_routes(session)


@router.post("/routes", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
async def create_route_route(
    payload: RouteWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_route(session, principal.tenant_id, payload)


@router.patch("/routes/{route_id}", response_model=RouteRead)
async def update_route_route(
    route_id: int,
    payload: RouteWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_route(session, route_id, payload)


@router.get("/routes/{route_id}/stops", response_model=list[StopRead])
async def list_stops_route(
    route_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_stops(session, route_id)


@router.put("/routes/{route_id}/stops", response_model=list[StopRead])
async def replace_stops_route(
    route_id: int,
    payload: StopBulk,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await replace_stops(session, principal.tenant_id, route_id, payload)


# ---- Allocations ----------------------------------------------------------


@router.get("/routes/{route_id}/allocations", response_model=list[AllocationRead])
async def list_allocations_route(
    route_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_allocations_for_route(session, route_id)


@router.post("/allocations", response_model=AllocationRead)
async def upsert_allocation_route(
    payload: AllocationWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_allocation(session, principal.tenant_id, payload)


@router.delete(
    "/allocations/{student_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def deallocate_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await deallocate(session, student_id)


# ---- Trips + GPS ----------------------------------------------------------


@router.post("/trips/start", response_model=TripRead)
async def start_trip_route(
    payload: TripStart,
    principal: AuthPrincipal = Depends(_driver_or_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await start_trip(session, principal.tenant_id, payload)


@router.post("/trips/{trip_id}/ping", response_model=TripRead)
async def ping_trip_route(
    trip_id: int,
    payload: GpsPing,
    principal: AuthPrincipal = Depends(_driver_or_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await ping_trip(session, trip_id, payload)


@router.post("/trips/{trip_id}/complete", response_model=TripRead)
async def complete_trip_route(
    trip_id: int,
    principal: AuthPrincipal = Depends(_driver_or_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await complete_trip(session, trip_id)


@router.get("/trips/{trip_id}", response_model=TripView)
async def trip_view_route(
    trip_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await trip_view(session, trip_id)


@router.post(
    "/trips/{trip_id}/boardings", response_model=BoardingRead
)
async def record_boarding_route(
    trip_id: int,
    payload: BoardingWrite,
    principal: AuthPrincipal = Depends(_driver_or_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await record_boarding(
        session, principal.tenant_id, principal.user_id, trip_id, payload
    )


@router.get(
    "/trips/{trip_id}/boardings", response_model=list[BoardingRead]
)
async def list_boardings_route(
    trip_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_boardings(session, trip_id)


# ---- Maintenance + fuel ---------------------------------------------------


@router.post("/maintenance", response_model=MaintenanceRead, status_code=status.HTTP_201_CREATED)
async def add_maintenance_route(
    payload: MaintenanceWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_maintenance(session, principal.tenant_id, payload)


@router.get("/buses/{bus_id}/maintenance", response_model=list[MaintenanceRead])
async def list_maintenance_route(
    bus_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_maintenance(session, bus_id)


@router.post("/fuel", response_model=FuelRead, status_code=status.HTTP_201_CREATED)
async def add_fuel_route(
    payload: FuelWrite,
    principal: AuthPrincipal = Depends(_transport_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_fuel(session, principal.tenant_id, payload)


@router.get("/buses/{bus_id}/fuel", response_model=list[FuelRead])
async def list_fuel_route(
    bus_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_fuel(session, bus_id)


# ---- Parent view ----------------------------------------------------------


parent_router = APIRouter(
    prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)]
)


@parent_router.get("/children/{student_id}/transport", response_model=ParentTransport)
async def parent_transport_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    return await parent_transport(session, student_id)


# ===========================================================================
# Phase 26 — skip toggle / SSE stream / transport invoicer.
# ===========================================================================


# ---- "Not coming today" toggle (parent app) ------------------------------


class _SkipBody(__import__("pydantic").BaseModel):
    skip_date: str
    direction: str = "pickup"
    reason: __import__("typing").Optional[str] = None


@parent_router.post(
    "/children/{student_id}/transport/skip",
    status_code=status.HTTP_201_CREATED,
)
async def parent_skip_route(
    student_id: int,
    payload: _SkipBody,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    """Parent flips "not coming today" for a single date + direction.
    Idempotent — re-tapping with the same date just updates the reason.
    """
    from datetime import date as _date
    from app.services.transport import upsert_skip

    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    try:
        d = _date.fromisoformat(payload.skip_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad skip_date")
    row = await upsert_skip(
        session,
        tenant_id=principal.tenant_id,
        student_id=student_id,
        skip_date=d,
        direction=payload.direction,
        reason=payload.reason,
    )
    return {"id": row.id, "skip_date": row.skip_date.isoformat(),
            "direction": row.direction, "reason": row.reason}


@parent_router.delete(
    "/children/{student_id}/transport/skip",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def parent_unskip_route(
    student_id: int,
    skip_date: str,
    direction: str = "pickup",
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    """Undo a skip — parent changed their mind."""
    from datetime import date as _date
    from app.services.transport import remove_skip

    try:
        d = _date.fromisoformat(skip_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad skip_date")
    await remove_skip(
        session, student_id=student_id, skip_date=d, direction=direction,
    )


# ---- Driver app: today's skip list -------------------------------------


@router.get("/routes/{route_id}/skips")
async def driver_skip_list_route(
    route_id: int,
    principal: AuthPrincipal = Depends(_driver_or_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Driver pulls this before / during a trip to know which students
    to bypass at their assigned stop today."""
    from app.services.transport import list_skips_for_today

    rows = await list_skips_for_today(session, route_id=route_id)
    return [
        {
            "student_id": r.student_id,
            "skip_date": r.skip_date.isoformat(),
            "direction": r.direction,
            "reason": r.reason,
        }
        for r in rows
    ]


# ---- SSE stream of trip GPS pings ---------------------------------------


@router.get("/trips/{trip_id}/stream")
async def trip_stream_route(
    trip_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Server-Sent Events — emits a tiny ``data: {...}\\n\\n`` payload
    every ~1 s while the trip is in progress so the parent's map can
    move smoothly instead of snapping every 30 s. Auto-stops when the
    trip's phase leaves ``in_progress``.

    Drop the 30 s poll on the parent side and just consume this — but
    keep the poll as a fallback for very old browsers / sketchy
    proxies that strip SSE.
    """
    import asyncio
    import json
    from fastapi.responses import StreamingResponse
    from app.services.transport import trip_position_snapshot

    async def event_stream():
        last_payload: dict | None = None
        # Cap at 30 minutes per connection so an idle stream doesn't
        # squat a worker forever.
        for _ in range(30 * 60):
            snap = await trip_position_snapshot(session, trip_id)
            if snap is None:
                break
            if snap != last_payload:
                yield f"data: {json.dumps(snap)}\n\n".encode("utf-8")
                last_payload = snap
            if snap.get("phase") not in {"in_progress", "scheduled"}:
                # Trip finished — let the client know and close.
                yield b"event: end\ndata: {}\n\n"
                break
            await asyncio.sleep(1)
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ---- Admin: monthly transport-invoice generator -------------------------


class _InvoiceBody(__import__("pydantic").BaseModel):
    year: int
    month: int
    due_day: int = 10


@router.post("/invoices/generate-monthly")
async def generate_monthly_transport_invoices_route(
    payload: _InvoiceBody,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """One-click: spin up a FeeInvoice per StudentTransport allocation
    using ``fee_per_month``. Idempotent on (student, structure, period)
    — re-running for the same month is a no-op for rows already
    invoiced. Result feeds straight into the parent's Fees screen."""
    from app.services.transport import generate_transport_invoices

    return await generate_transport_invoices(
        session,
        tenant_id=principal.tenant_id,
        year=payload.year,
        month=payload.month,
        due_day=payload.due_day,
    )
