"""Pydantic schemas for the Parent module (Phase 8)."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.parent import LeaveStatus, ParentAccessLevel, Relation


# ---- Children listing ------------------------------------------------------


class ChildSummary(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    current_class_label: Optional[str]
    photo_url: Optional[str]
    relation: Relation
    access_level: ParentAccessLevel
    is_primary: bool
    can_pay_fee: bool
    can_receive_notifications: bool


class ChildSwitch(BaseModel):
    student_id: int


class ParentSelfRead(BaseModel):
    parent_id: int
    user_id: int
    full_name: str
    phone: Optional[str]
    email: Optional[str]
    relation: Relation
    current_child_id: Optional[int]


# ---- Per-child dashboard ---------------------------------------------------


class ChildDashboard(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    current_class_label: Optional[str]
    is_active: bool
    pending_leaves: int
    documents_count: int
    sibling_ids: List[int]
    # Filled in once the upstream modules ship.
    today_attendance: Optional[str] = None  # Phase 9
    pending_homework: int = 0  # Phase 14
    fee_due_amount: float = 0.0  # Phase 11
    upcoming_events_count: int = 0  # already lit via Phase 5 events


# ---- Leave application -----------------------------------------------------


class LeaveCreate(BaseModel):
    student_id: int
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=2000)


class LeaveDecide(BaseModel):
    decision: LeaveStatus
    decision_remarks: Optional[str] = None


class LeaveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    parent_id: Optional[int]
    applied_by_user_id: Optional[int]
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus
    decision_remarks: Optional[str]
    decided_at: Optional[datetime]


# ---- Document vault --------------------------------------------------------


class StudentDocSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    label: Optional[str]
    path: str
    is_verified: bool


# ---- School-admin parent management ---------------------------------------


class ParentLink(BaseModel):
    parent_user_id: int
    relation: Relation = Relation.GUARDIAN
    access_level: ParentAccessLevel = ParentAccessLevel.PRIMARY
    is_primary: bool = False
    can_pay_fee: bool = True
    can_receive_notifications: bool = True


class ParentLinkRead(BaseModel):
    mapping_id: int
    parent_id: int
    parent_user_id: int
    parent_name: str
    parent_phone: Optional[str]
    parent_email: Optional[str]
    relation: Relation
    access_level: ParentAccessLevel
    is_primary: bool
    can_pay_fee: bool
    can_receive_notifications: bool


class ParentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str = Field(min_length=6, max_length=128)
    relation: Relation = Relation.GUARDIAN
    occupation: Optional[str] = None


class ParentPasswordReset(BaseModel):
    """Body for the school-admin "Set password" UI on the Family panel."""
    new_password: str = Field(min_length=6, max_length=128)


class ParentPasswordResetResult(BaseModel):
    user_id: int
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
