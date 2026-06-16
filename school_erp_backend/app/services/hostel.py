"""Hostel service (Phase 19)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hostel import (
    DisciplinaryRecord,
    Hostel,
    HostelAllocation,
    HostelLeave,
    HostelLeaveStatus,
    MessMenu,
    Room,
    RoomStatus,
    VisitorLog,
)
from app.models.parent import Student
from app.schemas.hostel import (
    AllocationWrite,
    DisciplinaryWrite,
    HostelLeaveApply,
    HostelLeaveDecide,
    HostelReports,
    HostelWrite,
    MessMenuWrite,
    RoomWrite,
    VisitorIn,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _D(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or "0"))


# ---- Hostels --------------------------------------------------------------


async def list_hostels(session: AsyncSession) -> list[Hostel]:
    return list((await session.execute(select(Hostel).order_by(Hostel.code))).scalars().all())


async def create_hostel(session: AsyncSession, tenant_id: int, payload: HostelWrite) -> Hostel:
    data = payload.model_dump()
    data["kind"] = payload.kind.value
    obj = Hostel(tenant_id=tenant_id, **data)
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate hostel code")
    await session.refresh(obj)
    return obj


async def update_hostel(session: AsyncSession, hostel_id: int, payload: HostelWrite) -> Hostel:
    obj = (await session.execute(select(Hostel).where(Hostel.id == hostel_id))).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v.value if hasattr(v, "value") else v)
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Rooms ----------------------------------------------------------------


async def list_rooms(session: AsyncSession, hostel_id: int) -> list[dict]:
    rooms = list(
        (
            await session.execute(
                select(Room).where(Room.hostel_id == hostel_id).order_by(Room.number)
            )
        ).scalars().all()
    )
    if not rooms:
        return []
    counts = dict(
        (
            await session.execute(
                select(HostelAllocation.room_id, func.count(HostelAllocation.id))
                .where(
                    HostelAllocation.room_id.in_([r.id for r in rooms]),
                    HostelAllocation.is_active.is_(True),
                )
                .group_by(HostelAllocation.room_id)
            )
        ).all()
    )
    return [
        {
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "occupied": int(counts.get(r.id, 0)),
        }
        for r in rooms
    ]


async def create_room(
    session: AsyncSession, tenant_id: int, hostel_id: int, payload: RoomWrite
) -> Room:
    if (
        await session.execute(select(Hostel).where(Hostel.id == hostel_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    data = payload.model_dump()
    data["status"] = payload.status.value
    obj = Room(tenant_id=tenant_id, hostel_id=hostel_id, **data)
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate room number")
    await session.refresh(obj)
    return obj


async def room_detail(session: AsyncSession, room_id: int) -> dict:
    room = (await session.execute(select(Room).where(Room.id == room_id))).scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    occ = list(
        (
            await session.execute(
                select(HostelAllocation).where(
                    HostelAllocation.room_id == room_id,
                    HostelAllocation.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    rows: list[dict] = []
    if occ:
        students = (
            await session.execute(
                select(Student).where(Student.id.in_([a.student_id for a in occ]))
            )
        ).scalars().all()
        for s in students:
            rows.append(
                {
                    "student_id": s.id,
                    "full_name": s.full_name,
                    "admission_number": s.admission_number,
                }
            )
    return {
        "room": {
            **{c.name: getattr(room, c.name) for c in room.__table__.columns},
            "occupied": len(occ),
        },
        "occupants": rows,
    }


# ---- Allocations ----------------------------------------------------------


async def upsert_allocation(
    session: AsyncSession, tenant_id: int, payload: AllocationWrite
) -> HostelAllocation:
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
    room = (
        await session.execute(select(Room).where(Room.id == payload.room_id))
    ).scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status == RoomStatus.UNDER_MAINTENANCE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is under maintenance",
        )

    obj = (
        await session.execute(
            select(HostelAllocation).where(HostelAllocation.student_id == payload.student_id)
        )
    ).scalar_one_or_none()

    # Capacity check (count active occupants other than this student).
    others = (
        await session.execute(
            select(func.count(HostelAllocation.id)).where(
                HostelAllocation.room_id == payload.room_id,
                HostelAllocation.is_active.is_(True),
                HostelAllocation.student_id != payload.student_id,
            )
        )
    ).scalar_one()
    if others >= room.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room is at capacity ({room.capacity})",
        )

    fee = payload.monthly_fee if payload.monthly_fee is not None else _D(room.monthly_fee)
    if obj is None:
        obj = HostelAllocation(
            tenant_id=tenant_id,
            student_id=payload.student_id,
            hostel_id=room.hostel_id,
            room_id=payload.room_id,
            occupied_from=payload.occupied_from,
            occupied_until=payload.occupied_until,
            monthly_fee=fee,
            is_active=True,
        )
        session.add(obj)
    else:
        obj.hostel_id = room.hostel_id
        obj.room_id = payload.room_id
        obj.occupied_from = payload.occupied_from
        obj.occupied_until = payload.occupied_until
        obj.monthly_fee = fee
        obj.is_active = True

    # Update room status if now full / freeing.
    new_count = others + 1
    room.status = (
        RoomStatus.FULL.value if new_count >= room.capacity else RoomStatus.AVAILABLE.value
    )
    await session.commit()
    await session.refresh(obj)
    return obj


async def vacate(session: AsyncSession, student_id: int) -> None:
    obj = (
        await session.execute(
            select(HostelAllocation).where(HostelAllocation.student_id == student_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    room = (
        await session.execute(select(Room).where(Room.id == obj.room_id))
    ).scalar_one_or_none()
    obj.is_active = False
    obj.occupied_until = obj.occupied_until or date.today()
    if room and room.status == RoomStatus.FULL.value:
        room.status = RoomStatus.AVAILABLE.value
    await session.commit()


# ---- Mess menu ------------------------------------------------------------


async def list_mess(
    session: AsyncSession, hostel_id: int, *, on_date: Optional[date] = None
) -> list[MessMenu]:
    stmt = select(MessMenu).where(MessMenu.hostel_id == hostel_id)
    if on_date:
        stmt = stmt.where(MessMenu.menu_date == on_date)
    return list((await session.execute(stmt.order_by(MessMenu.menu_date, MessMenu.meal))).scalars().all())


async def upsert_mess(
    session: AsyncSession, tenant_id: int, hostel_id: int, payload: MessMenuWrite
) -> MessMenu:
    if (await session.execute(select(Hostel).where(Hostel.id == hostel_id))).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    obj = (
        await session.execute(
            select(MessMenu).where(
                MessMenu.hostel_id == hostel_id,
                MessMenu.menu_date == payload.menu_date,
                MessMenu.meal == payload.meal.value,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        obj = MessMenu(
            tenant_id=tenant_id,
            hostel_id=hostel_id,
            menu_date=payload.menu_date,
            meal=payload.meal.value,
            items=payload.items,
        )
        session.add(obj)
    else:
        obj.items = payload.items
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Visitors -------------------------------------------------------------


async def visitor_check_in(
    session: AsyncSession,
    tenant_id: int,
    user_id: Optional[int],
    hostel_id: int,
    payload: VisitorIn,
) -> VisitorLog:
    obj = VisitorLog(
        tenant_id=tenant_id,
        hostel_id=hostel_id,
        student_id=payload.student_id,
        visitor_name=payload.visitor_name,
        visitor_phone=payload.visitor_phone,
        relation=payload.relation,
        purpose=payload.purpose,
        in_at=_now(),
        captured_by_user_id=user_id,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def visitor_check_out(session: AsyncSession, visitor_id: int) -> VisitorLog:
    obj = (
        await session.execute(select(VisitorLog).where(VisitorLog.id == visitor_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor entry not found")
    if obj.out_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already checked out")
    obj.out_at = _now()
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_visitors(
    session: AsyncSession, hostel_id: int, *, open_only: bool = False
) -> list[VisitorLog]:
    stmt = select(VisitorLog).where(VisitorLog.hostel_id == hostel_id)
    if open_only:
        stmt = stmt.where(VisitorLog.out_at.is_(None))
    return list((await session.execute(stmt.order_by(VisitorLog.id.desc()))).scalars().all())


# ---- Disciplinary ---------------------------------------------------------


async def add_disciplinary(
    session: AsyncSession,
    tenant_id: int,
    user_id: Optional[int],
    hostel_id: int,
    payload: DisciplinaryWrite,
) -> DisciplinaryRecord:
    # Validate ownership/existence up-front so the FK doesn't blow up
    # mid-flush with an opaque IntegrityError that surfaces as 500.
    hostel = (
        await session.execute(
            select(Hostel).where(
                Hostel.id == hostel_id, Hostel.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if hostel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found",
        )
    if payload.student_id is None or payload.student_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="student_id is required",
        )
    student = (
        await session.execute(
            select(Student).where(
                Student.id == payload.student_id,
                Student.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {payload.student_id} not found in this school",
        )
    if not (payload.title or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title is required",
        )

    obj = DisciplinaryRecord(
        tenant_id=tenant_id,
        hostel_id=hostel_id,
        student_id=payload.student_id,
        incident_on=payload.incident_on,
        severity=payload.severity.value,
        title=payload.title,
        description=payload.description,
        action_taken=payload.action_taken,
        recorded_by_user_id=user_id,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        logging.getLogger(__name__).exception("add_disciplinary IntegrityError")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not save disciplinary record: {getattr(e, 'orig', e)}",
        )
    await session.refresh(obj)
    return obj


async def list_disciplinary(
    session: AsyncSession, hostel_id: int, *, student_id: Optional[int] = None
) -> list[DisciplinaryRecord]:
    stmt = select(DisciplinaryRecord).where(DisciplinaryRecord.hostel_id == hostel_id)
    if student_id is not None:
        stmt = stmt.where(DisciplinaryRecord.student_id == student_id)
    return list((await session.execute(stmt.order_by(DisciplinaryRecord.incident_on.desc()))).scalars().all())


# ---- Hostel leave ---------------------------------------------------------


async def apply_leave(
    session: AsyncSession,
    tenant_id: int,
    hostel_id: int,
    payload: HostelLeaveApply,
) -> HostelLeave:
    if payload.to_date < payload.from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be on or after from_date",
        )
    hostel = (
        await session.execute(
            select(Hostel).where(
                Hostel.id == hostel_id, Hostel.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if hostel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found",
        )
    if payload.student_id is None or payload.student_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="student_id is required",
        )
    student = (
        await session.execute(
            select(Student).where(
                Student.id == payload.student_id,
                Student.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {payload.student_id} not found in this school",
        )
    if not (payload.reason or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required",
        )

    obj = HostelLeave(
        tenant_id=tenant_id,
        hostel_id=hostel_id,
        student_id=payload.student_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        reason=payload.reason,
        contact_phone=payload.contact_phone,
        status=HostelLeaveStatus.PENDING.value,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        logging.getLogger(__name__).exception("apply_leave IntegrityError")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not save leave: {getattr(e, 'orig', e)}",
        )
    await session.refresh(obj)
    return obj


async def decide_leave(
    session: AsyncSession,
    user_id: int,
    leave_id: int,
    payload: HostelLeaveDecide,
) -> HostelLeave:
    obj = (
        await session.execute(select(HostelLeave).where(HostelLeave.id == leave_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave not found")
    if obj.status != HostelLeaveStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave already {obj.status}",
        )
    if payload.decision not in {
        HostelLeaveStatus.APPROVED, HostelLeaveStatus.REJECTED,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="decision must be approved or rejected",
        )
    obj.status = payload.decision.value
    obj.decision_notes = payload.decision_notes
    obj.decided_at = _now()
    obj.decided_by_user_id = user_id
    await session.commit()
    await session.refresh(obj)
    return obj


async def mark_returned(
    session: AsyncSession, leave_id: int
) -> HostelLeave:
    obj = (
        await session.execute(select(HostelLeave).where(HostelLeave.id == leave_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave not found")
    if obj.status != HostelLeaveStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved leaves can be returned"
        )
    obj.status = HostelLeaveStatus.RETURNED.value
    obj.returned_at = _now()
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_leaves(
    session: AsyncSession,
    hostel_id: Optional[int] = None,
    *,
    status_filter: Optional[str] = None,
    student_id: Optional[int] = None,
) -> list[HostelLeave]:
    stmt = select(HostelLeave)
    if hostel_id is not None:
        stmt = stmt.where(HostelLeave.hostel_id == hostel_id)
    if status_filter:
        stmt = stmt.where(HostelLeave.status == status_filter)
    if student_id is not None:
        stmt = stmt.where(HostelLeave.student_id == student_id)
    return list((await session.execute(stmt.order_by(HostelLeave.id.desc()))).scalars().all())


# ---- Reports --------------------------------------------------------------


async def reports(session: AsyncSession) -> HostelReports:
    total_hostels = (await session.execute(select(func.count(Hostel.id)))).scalar_one()
    rooms = list((await session.execute(select(Room))).scalars().all())
    total_rooms = len(rooms)
    total_capacity = sum(r.capacity for r in rooms)
    occupied = (
        await session.execute(
            select(func.count(HostelAllocation.id)).where(HostelAllocation.is_active.is_(True))
        )
    ).scalar_one()
    pending_leaves = (
        await session.execute(
            select(func.count(HostelLeave.id)).where(
                HostelLeave.status == HostelLeaveStatus.PENDING.value
            )
        )
    ).scalar_one()
    open_disc = (
        await session.execute(select(func.count(DisciplinaryRecord.id)))
    ).scalar_one()
    return HostelReports(
        total_hostels=total_hostels,
        total_rooms=total_rooms,
        total_capacity=total_capacity,
        occupied=occupied,
        available_seats=max(0, total_capacity - occupied),
        pending_leaves=pending_leaves,
        open_disciplinary=open_disc,
    )


# ---- Parent view ----------------------------------------------------------


async def parent_hostel(session: AsyncSession, student_id: int) -> dict:
    alloc = (
        await session.execute(
            select(HostelAllocation).where(HostelAllocation.student_id == student_id)
        )
    ).scalar_one_or_none()
    leaves = list(
        (
            await session.execute(
                select(HostelLeave).where(HostelLeave.student_id == student_id)
                .order_by(HostelLeave.id.desc())
            )
        ).scalars().all()
    )
    if alloc is None:
        return {"student_id": student_id, "leaves": leaves}
    hostel = (
        await session.execute(select(Hostel).where(Hostel.id == alloc.hostel_id))
    ).scalar_one_or_none()
    room = (
        await session.execute(select(Room).where(Room.id == alloc.room_id))
    ).scalar_one_or_none()
    return {
        "student_id": student_id,
        "hostel_id": alloc.hostel_id,
        "hostel_name": hostel.name if hostel else None,
        "room_number": room.number if room else None,
        "monthly_fee": alloc.monthly_fee,
        "occupied_from": alloc.occupied_from,
        "leaves": leaves,
    }
