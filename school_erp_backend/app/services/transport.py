"""Transport service (Phase 18)."""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
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
    await session.commit()
    await session.refresh(obj)
    return obj


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
    existing = list(
        (
            await session.execute(select(Stop).where(Stop.route_id == route_id))
        ).scalars().all()
    )
    for s in existing:
        await session.delete(s)
    out: list[Stop] = []
    for s in payload.stops:
        obj = Stop(tenant_id=tenant_id, route_id=route_id, **s.model_dump())
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
