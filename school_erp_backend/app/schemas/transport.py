"""Transport schemas (Phase 18)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.transport import (
    BoardingEvent,
    BusStatus,
    DriverStatus,
    MaintenanceKind,
    TripDirection,
    TripPhase,
)


# ---- Buses + drivers ------------------------------------------------------


class BusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    registration_number: str
    code: Optional[str]
    capacity: int
    model: Optional[str]
    year_of_make: Optional[int]
    insurance_expiry: Optional[date]
    fitness_expiry: Optional[date]
    status: BusStatus
    notes: Optional[str]


class BusWrite(BaseModel):
    registration_number: str = Field(min_length=2, max_length=40)
    code: Optional[str] = None
    capacity: int = Field(default=40, gt=0)
    model: Optional[str] = None
    year_of_make: Optional[int] = None
    insurance_expiry: Optional[date] = None
    fitness_expiry: Optional[date] = None
    status: BusStatus = BusStatus.ACTIVE
    notes: Optional[str] = None


class DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    phone: Optional[str]
    license_number: str
    license_expiry: Optional[date]
    user_id: Optional[int]
    status: DriverStatus


class DriverWrite(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = None
    license_number: str = Field(min_length=2, max_length=40)
    license_expiry: Optional[date] = None
    user_id: Optional[int] = None
    status: DriverStatus = DriverStatus.ACTIVE


# ---- Routes + stops -------------------------------------------------------


class StopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    route_id: int
    sequence: int
    name: str
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    pickup_time: Optional[time]
    drop_time: Optional[time]


class StopWrite(BaseModel):
    sequence: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    pickup_time: Optional[time] = None
    drop_time: Optional[time] = None


class StopBulk(BaseModel):
    stops: List[StopWrite]


class RouteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    bus_id: Optional[int]
    driver_id: Optional[int]
    is_active: bool


class RouteWrite(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    bus_id: Optional[int] = None
    driver_id: Optional[int] = None
    is_active: bool = True


class RouteWithCounts(RouteRead):
    student_count: int
    stop_count: int


# ---- Allocations ----------------------------------------------------------


class AllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    route_id: int
    pickup_stop_id: Optional[int]
    drop_stop_id: Optional[int]
    fee_per_month: Decimal
    is_active: bool


class AllocationWrite(BaseModel):
    student_id: int
    route_id: int
    pickup_stop_id: Optional[int] = None
    drop_stop_id: Optional[int] = None
    fee_per_month: Decimal = Field(default=Decimal("0"), ge=0)
    is_active: bool = True


# ---- Trips + GPS ----------------------------------------------------------


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    route_id: int
    trip_date: date
    direction: TripDirection
    phase: TripPhase
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_lat: Optional[Decimal]
    last_lng: Optional[Decimal]
    last_speed_kph: Optional[Decimal]
    last_ping_at: Optional[datetime]


class TripStart(BaseModel):
    route_id: int
    trip_date: date
    direction: TripDirection = TripDirection.PICKUP


class GpsPing(BaseModel):
    lat: Decimal = Field(ge=-90, le=90)
    lng: Decimal = Field(ge=-180, le=180)
    speed_kph: Optional[Decimal] = Field(default=None, ge=0, le=300)


class TripView(TripRead):
    """Live snapshot used by parent + admin maps."""

    next_stop: Optional[StopRead]
    eta_minutes: Optional[int]


# ---- Boardings ------------------------------------------------------------


class BoardingWrite(BaseModel):
    student_id: int
    stop_id: Optional[int] = None
    event: BoardingEvent = BoardingEvent.BOARDED


class BoardingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trip_id: int
    student_id: int
    stop_id: Optional[int]
    event: BoardingEvent
    captured_at: datetime


# ---- Maintenance + fuel ---------------------------------------------------


class MaintenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bus_id: int
    kind: MaintenanceKind
    performed_on: date
    next_due_on: Optional[date]
    odometer_km: Optional[int]
    cost: Decimal
    notes: Optional[str]


class MaintenanceWrite(BaseModel):
    bus_id: int
    kind: MaintenanceKind = MaintenanceKind.SERVICE
    performed_on: date
    next_due_on: Optional[date] = None
    odometer_km: Optional[int] = None
    cost: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None


class FuelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bus_id: int
    fueled_on: date
    litres: Decimal
    cost: Decimal
    odometer_km: Optional[int]
    notes: Optional[str]


class FuelWrite(BaseModel):
    bus_id: int
    fueled_on: date
    litres: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)
    odometer_km: Optional[int] = None
    notes: Optional[str] = None


# ---- Parent view ----------------------------------------------------------


class ParentTransport(BaseModel):
    student_id: int
    route_id: Optional[int]
    route_name: Optional[str]
    pickup_stop: Optional[StopRead]
    drop_stop: Optional[StopRead]
    fee_per_month: Optional[Decimal]
    bus_registration: Optional[str]
    driver_name: Optional[str]
    driver_phone: Optional[str]
    today_trip: Optional[TripView]
