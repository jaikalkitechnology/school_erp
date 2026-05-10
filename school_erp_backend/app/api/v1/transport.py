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
    "school_admin", "principal", "vice_principal", "transport_manager",
    "coordinator",
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
