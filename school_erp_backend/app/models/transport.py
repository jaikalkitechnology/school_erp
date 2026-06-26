"""Transport entities (Phase 18)."""

from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)

from app.database import TenantBase


class BusStatus(str, enum.Enum):
    ACTIVE = "active"
    UNDER_MAINTENANCE = "under_maintenance"
    INACTIVE = "inactive"


class DriverStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    INACTIVE = "inactive"


class TripPhase(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TripDirection(str, enum.Enum):
    PICKUP = "pickup"
    DROP = "drop"


class BoardingEvent(str, enum.Enum):
    BOARDED = "boarded"
    DEBOARDED = "deboarded"
    NO_SHOW = "no_show"


class MaintenanceKind(str, enum.Enum):
    SERVICE = "service"
    REPAIR = "repair"
    INSPECTION = "inspection"


class Bus(TenantBase):
    __tablename__ = "transport_buses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "registration_number", name="uq_buses_reg"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    registration_number = Column(String(40), nullable=False)
    code = Column(String(20), nullable=True)
    capacity = Column(Integer, nullable=False, default=40)
    model = Column(String(80), nullable=True)
    year_of_make = Column(Integer, nullable=True)
    insurance_expiry = Column(Date, nullable=True)
    fitness_expiry = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default=BusStatus.ACTIVE.value)
    notes = Column(String(255), nullable=True)


class Driver(TenantBase):
    __tablename__ = "transport_drivers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "license_number", name="uq_drivers_license"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=True)
    license_number = Column(String(40), nullable=False)
    license_expiry = Column(Date, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default=DriverStatus.ACTIVE.value)


class Route(TenantBase):
    __tablename__ = "transport_routes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_routes_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    bus_id = Column(Integer, ForeignKey("transport_buses.id", ondelete="SET NULL"), nullable=True)
    driver_id = Column(Integer, ForeignKey("transport_drivers.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class Stop(TenantBase):
    __tablename__ = "transport_stops"
    __table_args__ = (
        Index("ix_stops_route_seq", "route_id", "sequence"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    name = Column(String(120), nullable=False)
    latitude = Column(Numeric(10, 6), nullable=True)
    longitude = Column(Numeric(10, 6), nullable=True)
    pickup_time = Column(Time, nullable=True)
    drop_time = Column(Time, nullable=True)


class StudentTransport(TenantBase):
    """Allocation of a student to a route + pickup stop. One row per
    student (current allocation); historical changes overwrite this row."""

    __tablename__ = "transport_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", name="uq_allocations_student"),
        Index("ix_allocations_route", "route_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False)
    pickup_stop_id = Column(Integer, ForeignKey("transport_stops.id", ondelete="SET NULL"), nullable=True)
    drop_stop_id = Column(Integer, ForeignKey("transport_stops.id", ondelete="SET NULL"), nullable=True)
    fee_per_month = Column(Numeric(8, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)


class Trip(TenantBase):
    """A single dated run of a route. Holds the latest GPS ping for
    parent live-view; deeper GPS history is intentionally out of scope
    until a real fleet stream is wired."""

    __tablename__ = "transport_trips"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "route_id", "trip_date", "direction",
            name="uq_trips_route_date_direction",
        ),
        Index("ix_trips_date", "trip_date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False)
    trip_date = Column(Date, nullable=False)
    direction = Column(String(10), nullable=False, default=TripDirection.PICKUP.value)
    phase = Column(String(15), nullable=False, default=TripPhase.SCHEDULED.value)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_lat = Column(Numeric(10, 6), nullable=True)
    last_lng = Column(Numeric(10, 6), nullable=True)
    last_speed_kph = Column(Numeric(6, 2), nullable=True)
    last_ping_at = Column(DateTime, nullable=True)


class TripBoarding(TenantBase):
    """One boarding event per (trip, student). Idempotent on the unique."""

    __tablename__ = "transport_trip_boardings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "trip_id", "student_id",
            name="uq_trip_boardings_unique",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    trip_id = Column(Integer, ForeignKey("transport_trips.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    stop_id = Column(Integer, ForeignKey("transport_stops.id", ondelete="SET NULL"), nullable=True)
    event = Column(String(15), nullable=False, default=BoardingEvent.BOARDED.value)
    captured_at = Column(DateTime, nullable=False)
    captured_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class TripSkip(TenantBase):
    """Parent's "not coming today" opt-out, scoped to a single date +
    direction. The driver app reads this so it knows to skip the
    student at the assigned stop; the push notifier reads it so we
    don't ping the parent with bus-arrived alerts they don't care
    about. One row per (student, date, direction)."""

    __tablename__ = "transport_trip_skips"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "skip_date", "direction",
            name="uq_trip_skip_unique",
        ),
        Index("ix_trip_skips_date_student", "skip_date", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False,
    )
    skip_date = Column(Date, nullable=False)
    direction = Column(String(10), nullable=False, default=TripDirection.PICKUP.value)
    reason = Column(String(255), nullable=True)


class MaintenanceLog(TenantBase):
    __tablename__ = "transport_maintenance_logs"
    __table_args__ = (
        Index("ix_maintenance_bus", "bus_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    bus_id = Column(Integer, ForeignKey("transport_buses.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), nullable=False, default=MaintenanceKind.SERVICE.value)
    performed_on = Column(Date, nullable=False)
    next_due_on = Column(Date, nullable=True)
    odometer_km = Column(Integer, nullable=True)
    cost = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(String(255), nullable=True)


class FuelLog(TenantBase):
    __tablename__ = "transport_fuel_logs"
    __table_args__ = (
        Index("ix_fuel_bus", "bus_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    bus_id = Column(Integer, ForeignKey("transport_buses.id", ondelete="CASCADE"), nullable=False)
    fueled_on = Column(Date, nullable=False)
    litres = Column(Numeric(8, 2), nullable=False, default=0)
    cost = Column(Numeric(10, 2), nullable=False, default=0)
    odometer_km = Column(Integer, nullable=True)
    notes = Column(String(255), nullable=True)
