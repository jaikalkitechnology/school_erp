"""Hostel schemas (Phase 19)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.hostel import (
    DisciplinarySeverity,
    HostelKind,
    HostelLeaveStatus,
    MealType,
    RoomStatus,
)


# ---- Hostels + rooms ------------------------------------------------------


class HostelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    kind: HostelKind
    warden_user_id: Optional[int]
    address: Optional[str]
    is_active: bool


class HostelWrite(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    kind: HostelKind = HostelKind.BOYS
    warden_user_id: Optional[int] = None
    address: Optional[str] = None
    is_active: bool = True


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hostel_id: int
    number: str
    floor: Optional[str]
    capacity: int
    monthly_fee: Decimal
    status: RoomStatus


class RoomWithOccupancy(RoomRead):
    occupied: int


class RoomWrite(BaseModel):
    number: str = Field(min_length=1, max_length=40)
    floor: Optional[str] = None
    capacity: int = Field(default=2, gt=0)
    monthly_fee: Decimal = Field(default=Decimal("0"), ge=0)
    status: RoomStatus = RoomStatus.AVAILABLE


# ---- Allocations ----------------------------------------------------------


class AllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    hostel_id: int
    room_id: int
    occupied_from: date
    occupied_until: Optional[date]
    monthly_fee: Decimal
    is_active: bool


class AllocationWrite(BaseModel):
    student_id: int
    room_id: int
    occupied_from: date
    occupied_until: Optional[date] = None
    monthly_fee: Optional[Decimal] = None  # falls back to room fee


class RoommateRow(BaseModel):
    student_id: int
    full_name: str
    admission_number: str


class RoomDetail(BaseModel):
    room: RoomWithOccupancy
    occupants: List[RoommateRow]


# ---- Mess menu ------------------------------------------------------------


class MessMenuRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hostel_id: int
    menu_date: date
    meal: MealType
    items: str


class MessMenuWrite(BaseModel):
    menu_date: date
    meal: MealType
    items: str = Field(min_length=1)


# ---- Visitor log ----------------------------------------------------------


class VisitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hostel_id: int
    student_id: int
    visitor_name: str
    visitor_phone: Optional[str]
    relation: Optional[str]
    in_at: datetime
    out_at: Optional[datetime]
    purpose: Optional[str]


class VisitorIn(BaseModel):
    student_id: int
    visitor_name: str = Field(min_length=1, max_length=120)
    visitor_phone: Optional[str] = None
    relation: Optional[str] = None
    purpose: Optional[str] = None


# ---- Disciplinary ---------------------------------------------------------


class DisciplinaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hostel_id: int
    student_id: int
    incident_on: date
    severity: DisciplinarySeverity
    title: str
    description: Optional[str]
    action_taken: Optional[str]


class DisciplinaryWrite(BaseModel):
    student_id: int
    incident_on: date
    severity: DisciplinarySeverity = DisciplinarySeverity.NOTE
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    action_taken: Optional[str] = None


# ---- Hostel leave ---------------------------------------------------------


class HostelLeaveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hostel_id: int
    student_id: int
    from_date: date
    to_date: date
    reason: str
    contact_phone: Optional[str]
    status: HostelLeaveStatus
    decided_at: Optional[datetime]
    returned_at: Optional[datetime]
    decision_notes: Optional[str]


class HostelLeaveApply(BaseModel):
    student_id: int
    from_date: date
    to_date: date
    reason: str = Field(min_length=1)
    contact_phone: Optional[str] = None


class HostelLeaveDecide(BaseModel):
    decision: HostelLeaveStatus
    decision_notes: Optional[str] = None


# ---- Reports --------------------------------------------------------------


class HostelReports(BaseModel):
    total_hostels: int
    total_rooms: int
    total_capacity: int
    occupied: int
    available_seats: int
    pending_leaves: int
    open_disciplinary: int


# ---- Parent view ----------------------------------------------------------


class ParentHostel(BaseModel):
    student_id: int
    hostel_id: Optional[int]
    hostel_name: Optional[str]
    room_number: Optional[str]
    monthly_fee: Optional[Decimal]
    occupied_from: Optional[date]
    leaves: List[HostelLeaveRead]
