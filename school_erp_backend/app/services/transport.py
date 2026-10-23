"""Transport service (Phase 18)."""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent import Student
from app.models.transport import (
    BoardingEvent,
    Bus,
    Driver,
    FuelLog,
    MaintenanceLog,
    Route,
    Stop,
    StudentTransport,
    Trip,
    TripBoarding,
    TripDirection,
    TripPhase,
    TripSkip,
)
from app.schemas.transport import (
    AllocationWrite,
    BoardingWrite,
    BusWrite,
    DriverWrite,
    FuelWrite,
    GpsPing,
    MaintenanceWrite,
    RouteWrite,
    StopBulk,
    TripStart,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _D(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or "0"))


# ---- Buses ----------------------------------------------------------------


async def list_buses(session: AsyncSession) -> list[Bus]:
    return list((await session.execute(select(Bus).order_by(Bus.id))).scalars().all())


async def create_bus(session: AsyncSession, tenant_id: int, payload: BusWrite) -> Bus:
    obj = Bus(tenant_id=tenant_id, **payload.model_dump())
    obj.status = payload.status.value
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate registration")
    await session.refresh(obj)
    return obj


async def update_bus(session: AsyncSession, bus_id: int, payload: BusWrite) -> Bus:
    obj = (await session.execute(select(Bus).where(Bus.id == bus_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v.value if hasattr(v, "value") else v)
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Drivers --------------------------------------------------------------


async def list_drivers(session: AsyncSession) -> list[Driver]:
    return list((await session.execute(select(Driver).order_by(Driver.id))).scalars().all())


async def create_driver(session: AsyncSession, tenant_id: int, payload: DriverWrite) -> Driver:
    data = payload.model_dump()
    data["status"] = payload.status.value
    obj = Driver(tenant_id=tenant_id, **data)
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate licence")
    await session.refresh(obj)
    return obj


async def update_driver(session: AsyncSession, driver_id: int, payload: DriverWrite) -> Driver:
    obj = (await session.execute(select(Driver).where(Driver.id == driver_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v.value if hasattr(v, "value") else v)
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Routes + stops -------------------------------------------------------


async def list_routes(session: AsyncSession) -> list[dict]:
    rows = list(
        (await session.execute(select(Route).order_by(Route.code))).scalars().all()
    )
    if not rows:
        return []
    route_ids = [r.id for r in rows]
    student_counts = dict(
        (
            await session.execute(
                select(StudentTransport.route_id, func.count(StudentTransport.id))
                .where(StudentTransport.route_id.in_(route_ids))
                .group_by(StudentTransport.route_id)
            )
        ).all()
    )
    stop_counts = dict(
        (
            await session.execute(
                select(Stop.route_id, func.count(Stop.id))
                .where(Stop.route_id.in_(route_ids))
                .group_by(Stop.route_id)
            )
        ).all()
    )
    return [
        {
            "id": r.id, "code": r.code, "name": r.name, "bus_id": r.bus_id,
            "driver_id": r.driver_id, "is_active": r.is_active,
            "student_count": int(student_counts.get(r.id, 0)),
            "stop_count": int(stop_counts.get(r.id, 0)),
        }
        for r in rows
    ]


async def create_route(session: AsyncSession, tenant_id: int, payload: RouteWrite) -> Route:
    obj = Route(tenant_id=tenant_id, **payload.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate route code")
    await session.refresh(obj)
    return obj


async def update_route(session: AsyncSession, route_id: int, payload: RouteWrite) -> Route:
    obj = (await session.execute(select(Route).where(Route.id == route_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate route code")
    await session.refresh(obj)
    return obj


async def delete_route(session: AsyncSession, route_id: int) -> None:
    """Delete a route and its stops. Refused while students ride it (move
    them to another route first) or once it has run trips, since the trip
    and boarding history would be lost with it — mark it inactive instead."""
    obj = (await session.execute(select(Route).where(Route.id == route_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    riders = (
        await session.execute(
            select(func.count(StudentTransport.id)).where(StudentTransport.route_id == route_id)
        )
    ).scalar() or 0
    if riders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{riders} student{'s are' if riders != 1 else ' is'} assigned to {obj.name}. "
            "Move them to another route first.",
        )
    trips = (
        await session.execute(select(func.count(Trip.id)).where(Trip.route_id == route_id))
    ).scalar() or 0
    if trips:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{obj.name} has trip history, so it can't be deleted. Mark it inactive instead.",
        )
    await session.execute(delete(Stop).where(Stop.route_id == route_id))
    await session.delete(obj)
    await session.commit()


async def list_stops(session: AsyncSession, route_id: int) -> list[Stop]:
    return list(
        (
            await session.execute(
                select(Stop).where(Stop.route_id == route_id).order_by(Stop.sequence)
            )
        ).scalars().all()
    )


async def replace_stops(
    session: AsyncSession, tenant_id: int, route_id: int, payload: StopBulk
) -> list[Stop]:
    if (
        await session.execute(select(Route).where(Route.id == route_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    seqs = [s.sequence for s in payload.stops]
    if len(seqs) != len(set(seqs)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate sequence in stops",
        )
    existing = {
        s.id: s
        for s in (
            await session.execute(select(Stop).where(Stop.route_id == route_id))
        ).scalars().all()
    }
    unknown = [s.id for s in payload.stops if s.id is not None and s.id not in existing]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stop does not belong to this route",
        )
    # Stops sent with their id are updated in place, so students' pickup /
    # drop stops survive a re-save. Stops left out are removed and anyone
    # picked up there is left without a stop.
    kept = {s.id for s in payload.stops if s.id is not None}
    removed = [sid for sid in existing if sid not in kept]
    if removed:
        await session.execute(
            update(StudentTransport)
            .where(StudentTransport.pickup_stop_id.in_(removed))
            .values(pickup_stop_id=None)
        )
        await session.execute(
            update(StudentTransport)
            .where(StudentTransport.drop_stop_id.in_(removed))
            .values(drop_stop_id=None)
        )
        for sid in removed:
            await session.delete(existing[sid])
    out: list[Stop] = []
    for s in payload.stops:
        fields = s.model_dump(exclude={"id"})
        if s.id is not None:
            obj = existing[s.id]
            for k, v in fields.items():
                setattr(obj, k, v)
        else:
            obj = Stop(tenant_id=tenant_id, route_id=route_id, **fields)
            session.add(obj)
        out.append(obj)
    await session.commit()
    for o in out:
        await session.refresh(o)
    return out


# ---- Allocations ----------------------------------------------------------


async def list_allocations_for_route(
    session: AsyncSession, route_id: int
) -> list[StudentTransport]:
    return list(
        (
            await session.execute(
                select(StudentTransport).where(StudentTransport.route_id == route_id)
            )
        ).scalars().all()
    )


async def upsert_allocation(
    session: AsyncSession, tenant_id: int, payload: AllocationWrite
) -> StudentTransport:
    if (
        await session.execute(
            select(Student).where(
                Student.id == payload.student_id, Student.is_active.is_(True)
            )
        )
    ).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found / inactive"
        )
    if (
        await session.execute(select(Route).where(Route.id == payload.route_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    # Stops must belong to that route.
    for stop_id in (payload.pickup_stop_id, payload.drop_stop_id):
        if stop_id is None:
            continue
        stop = (
            await session.execute(select(Stop).where(Stop.id == stop_id))
        ).scalar_one_or_none()
        if stop is None or stop.route_id != payload.route_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stop {stop_id} does not belong to the route",
            )

    obj = (
        await session.execute(
            select(StudentTransport).where(StudentTransport.student_id == payload.student_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        obj = StudentTransport(tenant_id=tenant_id, **payload.model_dump())
        session.add(obj)
    else:
        for k, v in payload.model_dump().items():
            setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


async def deallocate(session: AsyncSession, student_id: int) -> None:
    obj = (
        await session.execute(
            select(StudentTransport).where(StudentTransport.student_id == student_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    await session.delete(obj)
    await session.commit()


# ---- Trips + GPS ----------------------------------------------------------


async def start_trip(
    session: AsyncSession, tenant_id: int, payload: TripStart
) -> Trip:
    if (
        await session.execute(select(Route).where(Route.id == payload.route_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    obj = (
        await session.execute(
            select(Trip).where(
                Trip.route_id == payload.route_id,
                Trip.trip_date == payload.trip_date,
                Trip.direction == payload.direction.value,
            )
        )
    ).scalar_one_or_none()
    now = _now()
    if obj is None:
        obj = Trip(
            tenant_id=tenant_id,
            route_id=payload.route_id,
            trip_date=payload.trip_date,
            direction=payload.direction.value,
            phase=TripPhase.IN_PROGRESS.value,
            started_at=now,
        )
        session.add(obj)
    else:
        if obj.phase == TripPhase.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Trip already completed"
            )
        obj.phase = TripPhase.IN_PROGRESS.value
        obj.started_at = obj.started_at or now
    await session.commit()
    await session.refresh(obj)

    # Push to every parent on the route: "bus has left school".
    route = (
        await session.execute(select(Route).where(Route.id == obj.route_id))
    ).scalar_one_or_none()
    await _notify_route_event(
        session,
        tenant_id=tenant_id,
        route_id=obj.route_id,
        template_code="transport.bus_departed",
        context={
            "route": route.name if route else f"Route #{obj.route_id}",
            "direction": obj.direction,
        },
        deeplink=f"/transport/trips/{obj.id}",
        source_id=obj.id,
    )
    return obj


async def ping_trip(session: AsyncSession, trip_id: int, payload: GpsPing) -> Trip:
    trip = (
        await session.execute(select(Trip).where(Trip.id == trip_id))
    ).scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.phase not in {TripPhase.IN_PROGRESS.value, TripPhase.SCHEDULED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trip is {trip.phase}; cannot accept pings",
        )
    trip.last_lat = payload.lat
    trip.last_lng = payload.lng
    trip.last_speed_kph = payload.speed_kph
    trip.last_ping_at = _now()
    if trip.phase == TripPhase.SCHEDULED.value:
        trip.phase = TripPhase.IN_PROGRESS.value
        trip.started_at = trip.started_at or trip.last_ping_at
    await session.commit()
    await session.refresh(trip)

    # Geofence: emit approaching / arrived pushes once per stop, per
    # trip, per stage. Cheap enough to run every ping.
    await maybe_geofence_push(session, trip=trip)
    return trip


async def complete_trip(session: AsyncSession, trip_id: int) -> Trip:
    trip = (
        await session.execute(select(Trip).where(Trip.id == trip_id))
    ).scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    trip.phase = TripPhase.COMPLETED.value
    trip.completed_at = _now()
    await session.commit()
    await session.refresh(trip)
    return trip


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def trip_view(session: AsyncSession, trip_id: int) -> dict:
    trip = (
        await session.execute(select(Trip).where(Trip.id == trip_id))
    ).scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    stops = list(
        (
            await session.execute(
                select(Stop).where(Stop.route_id == trip.route_id).order_by(Stop.sequence)
            )
        ).scalars().all()
    )
    next_stop = None
    eta_minutes: Optional[int] = None
    if trip.last_lat is not None and trip.last_lng is not None and stops:
        # Pick the stop with the smallest distance whose sequence index is
        # greater than the closest visited stop. Heuristic but enough for
        # ETA without a routing engine.
        latf = float(trip.last_lat)
        lngf = float(trip.last_lng)
        best: tuple[float, Stop] | None = None
        for s in stops:
            if s.latitude is None or s.longitude is None:
                continue
            d = _haversine_km(latf, lngf, float(s.latitude), float(s.longitude))
            if best is None or d < best[0]:
                best = (d, s)
        if best is not None:
            speed = float(trip.last_speed_kph or 25)
            speed = speed if speed > 0 else 25
            eta_minutes = int(round((best[0] / speed) * 60))
            # The stop *closest* to the bus is "next" in the simple model.
            next_stop = best[1]
    base = {c.name: getattr(trip, c.name) for c in trip.__table__.columns}
    base["next_stop"] = (
        {c.name: getattr(next_stop, c.name) for c in next_stop.__table__.columns}
        if next_stop else None
    )
    base["eta_minutes"] = eta_minutes
    return base


# ---- Boardings ------------------------------------------------------------


async def record_boarding(
    session: AsyncSession,
    tenant_id: int,
    user_id: Optional[int],
    trip_id: int,
    payload: BoardingWrite,
) -> TripBoarding:
    trip = (await session.execute(select(Trip).where(Trip.id == trip_id))).scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if (
        await session.execute(
            select(Student).where(Student.id == payload.student_id)
        )
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found")

    obj = (
        await session.execute(
            select(TripBoarding).where(
                TripBoarding.trip_id == trip_id,
                TripBoarding.student_id == payload.student_id,
            )
        )
    ).scalar_one_or_none()
    now = _now()
    if obj is None:
        obj = TripBoarding(
            tenant_id=tenant_id,
            trip_id=trip_id,
            student_id=payload.student_id,
            stop_id=payload.stop_id,
            event=payload.event.value,
            captured_at=now,
            captured_by_user_id=user_id,
        )
        session.add(obj)
    else:
        obj.stop_id = payload.stop_id
        obj.event = payload.event.value
        obj.captured_at = now
        obj.captured_by_user_id = user_id
    await session.commit()
    await session.refresh(obj)

    # Push to this child's parents on every BOARDED / DEBOARDED event.
    student = (
        await session.execute(
            select(Student).where(Student.id == payload.student_id)
        )
    ).scalar_one_or_none()
    if student is not None and obj.event in {
        BoardingEvent.BOARDED.value, BoardingEvent.DEBOARDED.value,
    }:
        code = (
            "transport.boarded" if obj.event == BoardingEvent.BOARDED.value
            else "transport.dropped"
        )
        await _notify_student_event(
            session,
            tenant_id=tenant_id,
            student_id=student.id,
            template_code=code,
            context={
                "student": student.full_name,
                "time": now.strftime("%H:%M"),
            },
            deeplink=f"/transport/trips/{trip_id}",
            source_id=obj.id,
        )
    return obj


async def list_boardings(session: AsyncSession, trip_id: int) -> list[TripBoarding]:
    return list(
        (
            await session.execute(
                select(TripBoarding).where(TripBoarding.trip_id == trip_id)
            )
        ).scalars().all()
    )


# ---- Maintenance + fuel ---------------------------------------------------


async def add_maintenance(
    session: AsyncSession, tenant_id: int, payload: MaintenanceWrite
) -> MaintenanceLog:
    if (await session.execute(select(Bus).where(Bus.id == payload.bus_id))).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    data = payload.model_dump()
    data["kind"] = payload.kind.value
    obj = MaintenanceLog(tenant_id=tenant_id, **data)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_maintenance(session: AsyncSession, bus_id: int) -> list[MaintenanceLog]:
    return list(
        (
            await session.execute(
                select(MaintenanceLog)
                .where(MaintenanceLog.bus_id == bus_id)
                .order_by(MaintenanceLog.performed_on.desc())
            )
        ).scalars().all()
    )


async def add_fuel(
    session: AsyncSession, tenant_id: int, payload: FuelWrite
) -> FuelLog:
    if (await session.execute(select(Bus).where(Bus.id == payload.bus_id))).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    obj = FuelLog(tenant_id=tenant_id, **payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_fuel(session: AsyncSession, bus_id: int) -> list[FuelLog]:
    return list(
        (
            await session.execute(
                select(FuelLog).where(FuelLog.bus_id == bus_id).order_by(FuelLog.fueled_on.desc())
            )
        ).scalars().all()
    )


# ---- Parent view ----------------------------------------------------------


async def parent_transport(session: AsyncSession, student_id: int) -> dict:
    alloc = (
        await session.execute(
            select(StudentTransport).where(StudentTransport.student_id == student_id)
        )
    ).scalar_one_or_none()
    if alloc is None:
        return {"student_id": student_id}
    route = (
        await session.execute(select(Route).where(Route.id == alloc.route_id))
    ).scalar_one_or_none()
    pickup = drop = None
    if alloc.pickup_stop_id:
        pickup = (
            await session.execute(select(Stop).where(Stop.id == alloc.pickup_stop_id))
        ).scalar_one_or_none()
    if alloc.drop_stop_id:
        drop = (
            await session.execute(select(Stop).where(Stop.id == alloc.drop_stop_id))
        ).scalar_one_or_none()
    bus = None
    driver = None
    if route and route.bus_id:
        bus = (await session.execute(select(Bus).where(Bus.id == route.bus_id))).scalar_one_or_none()
    if route and route.driver_id:
        driver = (
            await session.execute(select(Driver).where(Driver.id == route.driver_id))
        ).scalar_one_or_none()

    today_trip_view = None
    if route:
        today_trip = (
            await session.execute(
                select(Trip).where(
                    Trip.route_id == route.id,
                    Trip.trip_date == date.today(),
                    Trip.phase.in_([TripPhase.IN_PROGRESS.value, TripPhase.SCHEDULED.value]),
                ).order_by(Trip.id.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if today_trip is not None:
            today_trip_view = await trip_view(session, today_trip.id)

    def _stop_dict(s):
        return None if s is None else {c.name: getattr(s, c.name) for c in s.__table__.columns}

    return {
        "student_id": student_id,
        "route_id": route.id if route else None,
        "route_name": route.name if route else None,
        "pickup_stop": _stop_dict(pickup),
        "drop_stop": _stop_dict(drop),
        "fee_per_month": alloc.fee_per_month,
        "bus_registration": bus.registration_number if bus else None,
        "driver_name": driver.full_name if driver else None,
        "driver_phone": driver.phone if driver else None,
        "today_trip": today_trip_view,
    }


# ============================================================================
# Phase 26 — skip toggle / push notifications / transport fees / SSE stream.
# ============================================================================


# ---- "Not coming today" -----------------------------------------------------


async def list_skips_for_today(
    session: AsyncSession, *, route_id: int, on_date: Optional[date] = None,
) -> list[TripSkip]:
    """Skip rows for every student on this route on this date. Driver
    app reads this so it knows whose stop to bypass."""
    on_date = on_date or date.today()
    student_ids = list(
        (
            await session.execute(
                select(StudentTransport.student_id).where(
                    StudentTransport.route_id == route_id,
                    StudentTransport.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    if not student_ids:
        return []
    return list(
        (
            await session.execute(
                select(TripSkip).where(
                    TripSkip.student_id.in_(student_ids),
                    TripSkip.skip_date == on_date,
                )
            )
        ).scalars().all()
    )


async def upsert_skip(
    session: AsyncSession,
    *,
    tenant_id: int,
    student_id: int,
    skip_date: date,
    direction: str = TripDirection.PICKUP.value,
    reason: Optional[str] = None,
) -> TripSkip:
    """Idempotent on (student_id, skip_date, direction) — reusing the
    same row means the parent can edit the reason without piling up
    duplicates."""
    existing = (
        await session.execute(
            select(TripSkip).where(
                TripSkip.student_id == student_id,
                TripSkip.skip_date == skip_date,
                TripSkip.direction == direction,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if reason is not None:
            existing.reason = reason
        await session.commit()
        return existing
    row = TripSkip(
        tenant_id=tenant_id,
        student_id=student_id,
        skip_date=skip_date,
        direction=direction,
        reason=reason,
    )
    session.add(row)
    await session.commit()
    return row


async def remove_skip(
    session: AsyncSession,
    *,
    student_id: int,
    skip_date: date,
    direction: str = TripDirection.PICKUP.value,
) -> None:
    """Parent changed their mind / wants to un-skip a future date."""
    row = (
        await session.execute(
            select(TripSkip).where(
                TripSkip.student_id == student_id,
                TripSkip.skip_date == skip_date,
                TripSkip.direction == direction,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.commit()


# ---- Push notification hooks -----------------------------------------------


async def _parent_users_for_students(
    session: AsyncSession, *, student_ids: list[int],
):
    """Resolve User rows for the parents linked to the given students.
    Used by the transport push hooks to fan out FCM messages."""
    if not student_ids:
        return []
    from app.models.auth import User
    from app.models.parent import Parent, ParentChildMapping

    rows = list(
        (
            await session.execute(
                select(User)
                .join(Parent, Parent.user_id == User.id)
                .join(
                    ParentChildMapping,
                    ParentChildMapping.parent_id == Parent.id,
                )
                .where(
                    ParentChildMapping.student_id.in_(student_ids),
                    User.is_active.is_(True),
                )
            )
        ).unique().scalars().all()
    )
    return rows


async def _notify_route_event(
    session: AsyncSession,
    *,
    tenant_id: int,
    route_id: int,
    template_code: str,
    context: dict,
    deeplink: Optional[str] = None,
    source_id: Optional[int] = None,
) -> None:
    """Fan an FCM push to the parents of every active rider on a
    route. Skip rows for the current date are honoured so opted-out
    parents don't get the buzz. Failures are swallowed — the trip /
    boarding row is already committed by the caller."""
    try:
        from app.services.comms import notify
        from app.services.push_dispatch import drain_pending_push_outbox_ids

        student_ids = list(
            (
                await session.execute(
                    select(StudentTransport.student_id).where(
                        StudentTransport.route_id == route_id,
                        StudentTransport.is_active.is_(True),
                    )
                )
            ).scalars().all()
        )
        if not student_ids:
            return
        # Drop students who opted out today.
        skipped_today = {
            sid for (sid,) in (
                await session.execute(
                    select(TripSkip.student_id).where(
                        TripSkip.student_id.in_(student_ids),
                        TripSkip.skip_date == date.today(),
                    )
                )
            ).all()
        }
        active_ids = [sid for sid in student_ids if sid not in skipped_today]
        if not active_ids:
            return
        users = await _parent_users_for_students(session, student_ids=active_ids)
        if not users:
            return
        _, ids = await notify(
            session,
            tenant_id=tenant_id,
            template_code=template_code,
            recipients=users,
            context=context,
            deeplink=deeplink,
            source_type="transport_trip",
            source_id=source_id,
            kind="transport",
        )
        if ids:
            await drain_pending_push_outbox_ids(session, ids)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "transport notify %s failed (route_id=%s)", template_code, route_id,
        )


async def _notify_student_event(
    session: AsyncSession,
    *,
    tenant_id: int,
    student_id: int,
    template_code: str,
    context: dict,
    deeplink: Optional[str] = None,
    source_id: Optional[int] = None,
) -> None:
    """Fan an FCM push to a single student's parent. Used for
    boarded / dropped per-child events."""
    try:
        from app.services.comms import notify
        from app.services.push_dispatch import drain_pending_push_outbox_ids

        users = await _parent_users_for_students(session, student_ids=[student_id])
        if not users:
            return
        _, ids = await notify(
            session,
            tenant_id=tenant_id,
            template_code=template_code,
            recipients=users,
            context=context,
            deeplink=deeplink,
            source_type="transport_boarding",
            source_id=source_id,
            kind="transport",
        )
        if ids:
            await drain_pending_push_outbox_ids(session, ids)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "transport notify %s failed (student_id=%s)", template_code, student_id,
        )


# ---- Approaching-stop watcher (called from every GPS ping) ----------------


# When the bus is within this many km of a stop, parents of students who
# board / disembark at that stop get a single "approaching" push. Stored
# in a tiny per-trip set so we don't spam every ping.
_APPROACH_RADIUS_KM = 0.7
_ARRIVE_RADIUS_KM = 0.15
# In-process suppression: prevents one ping-burst from firing the same
# notification twice. Wiped on process restart, which is fine — a fresh
# ping after restart can buzz once, no big deal.
_NOTIFY_SEEN: set[tuple[int, int, str]] = set()


async def maybe_geofence_push(
    session: AsyncSession,
    *,
    trip: Trip,
) -> None:
    """Called from ``ping_trip`` after the GPS row is updated. Checks
    every stop on the route; for any stop the bus is now within
    ``_APPROACH_RADIUS_KM`` of, fires a single
    ``transport.approaching_stop`` push to the parents of the riders
    boarding at that stop. Same logic again at ``_ARRIVE_RADIUS_KM`` for
    ``transport.arrived_stop``."""
    if trip.last_lat is None or trip.last_lng is None:
        return
    lat = float(trip.last_lat)
    lng = float(trip.last_lng)
    stops = list(
        (
            await session.execute(
                select(Stop).where(Stop.route_id == trip.route_id)
            )
        ).scalars().all()
    )
    if not stops:
        return

    for s in stops:
        if s.latitude is None or s.longitude is None:
            continue
        d_km = _haversine_km(lat, lng, float(s.latitude), float(s.longitude))
        if d_km > _APPROACH_RADIUS_KM:
            continue

        stage = "arrived" if d_km <= _ARRIVE_RADIUS_KM else "approaching"
        key = (trip.id, s.id, stage)
        if key in _NOTIFY_SEEN:
            continue
        _NOTIFY_SEEN.add(key)

        # Parents who board / disembark at this stop.
        student_ids = list(
            (
                await session.execute(
                    select(StudentTransport.student_id).where(
                        StudentTransport.is_active.is_(True),
                        (StudentTransport.pickup_stop_id == s.id)
                        | (StudentTransport.drop_stop_id == s.id),
                    )
                )
            ).scalars().all()
        )
        skipped_today = {
            sid for (sid,) in (
                await session.execute(
                    select(TripSkip.student_id).where(
                        TripSkip.student_id.in_(student_ids),
                        TripSkip.skip_date == date.today(),
                    )
                )
            ).all()
        }
        active = [sid for sid in student_ids if sid not in skipped_today]
        if not active:
            continue
        users = await _parent_users_for_students(session, student_ids=active)
        if not users:
            continue

        from app.services.comms import notify
        from app.services.push_dispatch import drain_pending_push_outbox_ids

        code = (
            "transport.arrived_stop" if stage == "arrived"
            else "transport.approaching_stop"
        )
        _, ids = await notify(
            session,
            tenant_id=trip.tenant_id,
            template_code=code,
            recipients=users,
            context={"stop": s.name},
            source_type="transport_trip",
            source_id=trip.id,
            kind="transport",
        )
        if ids:
            await drain_pending_push_outbox_ids(session, ids)


# ---- SSE-friendly view --------------------------------------------------


async def trip_position_snapshot(
    session: AsyncSession, trip_id: int,
) -> Optional[dict]:
    """Tiny payload the SSE stream emits every second-ish. Just the
    fields a moving-on-map UI needs — no joins on stops or boardings."""
    trip = (
        await session.execute(select(Trip).where(Trip.id == trip_id))
    ).scalar_one_or_none()
    if trip is None:
        return None
    return {
        "trip_id": trip.id,
        "phase": trip.phase,
        "last_lat": float(trip.last_lat) if trip.last_lat is not None else None,
        "last_lng": float(trip.last_lng) if trip.last_lng is not None else None,
        "last_speed_kph": (
            float(trip.last_speed_kph) if trip.last_speed_kph is not None else None
        ),
        "last_ping_at": trip.last_ping_at.isoformat() if trip.last_ping_at else None,
    }


# ---- Transport fee invoicer ------------------------------------------------


async def generate_transport_invoices(
    session: AsyncSession,
    *,
    tenant_id: int,
    year: int,
    month: int,
    due_day: int = 10,
) -> dict:
    """Bulk-create monthly transport invoices from
    ``StudentTransport.fee_per_month``. Idempotent on
    ``(student_id, structure_id, period_start)`` — re-running for the
    same month is a no-op for students whose invoice already exists.

    A synthetic FeeStructure ("Transport — YYYY-MM") is upserted per
    tenant + month so the invoices link cleanly into the existing Fees
    UI (parent's Fees screen + admin reports).
    """
    from datetime import date as _date
    from decimal import Decimal as _Dec

    from app.models.fees import (
        FeeCategory,
        FeeInvoice,
        FeeInvoiceStatus,
        FeeStructure,
        FeeStructureFrequency,
    )
    from app.services.fees import _next_invoice_number

    period_start = _date(year, month, 1)
    period_end = (
        _date(year + 1, 1, 1) if month == 12 else _date(year, month + 1, 1)
    )
    due_day = max(1, min(due_day, 28))
    due_date = _date(year, month, due_day)

    # Per-tenant Transport category — created on demand once.
    category = (
        await session.execute(
            select(FeeCategory).where(
                FeeCategory.tenant_id == tenant_id,
                FeeCategory.code == "transport",
            )
        )
    ).scalar_one_or_none()
    if category is None:
        category = FeeCategory(
            tenant_id=tenant_id, code="transport", name="Transport",
        )
        session.add(category)
        await session.flush()

    # Structure per (year, month) — pricing is per allocation, so the
    # structure's amount is a sentinel; the invoice carries the real
    # per-student total.
    structure_name = f"Transport — {year:04d}-{month:02d}"
    structure = (
        await session.execute(
            select(FeeStructure).where(
                FeeStructure.tenant_id == tenant_id,
                FeeStructure.name == structure_name,
            )
        )
    ).scalar_one_or_none()
    if structure is None:
        structure = FeeStructure(
            tenant_id=tenant_id,
            category_id=category.id,
            class_def_id=None,
            name=structure_name,
            amount=_Dec("0"),
            frequency=FeeStructureFrequency.MONTHLY.value,
            due_day=due_day,
        )
        session.add(structure)
        await session.flush()

    allocations = list(
        (
            await session.execute(
                select(StudentTransport).where(
                    StudentTransport.is_active.is_(True),
                    StudentTransport.fee_per_month > 0,
                )
            )
        ).scalars().all()
    )

    created = 0
    skipped = 0
    for alloc in allocations:
        existing = (
            await session.execute(
                select(FeeInvoice).where(
                    FeeInvoice.student_id == alloc.student_id,
                    FeeInvoice.structure_id == structure.id,
                    FeeInvoice.period_start == period_start,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue
        total = _D(alloc.fee_per_month)
        invoice = FeeInvoice(
            tenant_id=tenant_id,
            student_id=alloc.student_id,
            structure_id=structure.id,
            category_id=category.id,
            invoice_number=_next_invoice_number(tenant_id),
            period_start=period_start,
            period_end=period_end,
            due_date=due_date,
            base_amount=total,
            discount_amount=_Dec("0"),
            late_fee_amount=_Dec("0"),
            total_amount=total,
            paid_amount=_Dec("0"),
            status=FeeInvoiceStatus.PENDING.value,
        )
        session.add(invoice)
        created += 1
    await session.commit()
    return {
        "structure_id": structure.id,
        "created": created,
        "skipped": skipped,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
    }
