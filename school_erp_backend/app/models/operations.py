"""Phase 28 operational modules: Admissions, Finance, Payroll, Inventory,
Visitor, Health, Certificates, Discipline, Notices, Alumni, Sports.

Everything here is tenant-scoped via ``TenantBase`` — the auto-filter
in ``tenant_scoped_session`` handles multi-tenancy without per-query
where clauses in the routers.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import TenantBase


# ---------------------------------------------------------------------------
# 1. Admissions — enquiry → applied → tested → offered → confirmed
# ---------------------------------------------------------------------------


class AdmissionStage(str, enum.Enum):
    ENQUIRY = "enquiry"
    APPLIED = "applied"
    TESTED = "tested"
    OFFERED = "offered"
    CONFIRMED = "confirmed"
    CONVERTED = "converted"  # became a Student row
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class AdmissionInquiry(TenantBase):
    __tablename__ = "admission_inquiries"
    __table_args__ = (
        Index("ix_adm_inq_tenant_stage", "tenant_id", "stage"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    child_full_name = Column(String(180), nullable=False)
    child_dob = Column(Date, nullable=True)
    class_applying_for = Column(String(40), nullable=True)
    parent_name = Column(String(180), nullable=True)
    parent_phone = Column(String(20), nullable=True)
    parent_email = Column(String(180), nullable=True)
    source = Column(String(40), nullable=True)  # walk-in, website, referral, ad
    stage = Column(
        String(20), nullable=False, default=AdmissionStage.ENQUIRY.value,
    )
    notes = Column(Text, nullable=True)
    test_date = Column(Date, nullable=True)
    test_score = Column(Numeric(5, 2), nullable=True)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True,
    )
    handled_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )


# ---------------------------------------------------------------------------
# 2. Accounts / Finance — vendors + expenses
# ---------------------------------------------------------------------------


class Vendor(TenantBase):
    __tablename__ = "vendors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_vendor_name"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    name = Column(String(180), nullable=False)
    contact_person = Column(String(120), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(180), nullable=True)
    gst_number = Column(String(40), nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"


class Expense(TenantBase):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_tenant_date", "tenant_id", "spent_on"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    category = Column(String(80), nullable=False)
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True,
    )
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    spent_on = Column(Date, nullable=False)
    paid_from = Column(String(40), nullable=True)  # cash / bank / upi
    invoice_ref = Column(String(80), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(
        String(12), nullable=False, default=ExpenseStatus.PENDING.value,
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    approved_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    approved_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# 3. Payroll / HR — salary structure + monthly payslips
# ---------------------------------------------------------------------------


class SalaryStructure(TenantBase):
    __tablename__ = "salary_structures"
    __table_args__ = (
        Index("ix_salary_user", "tenant_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    basic = Column(Numeric(12, 2), nullable=False, default=0)
    hra = Column(Numeric(12, 2), nullable=False, default=0)
    allowances = Column(JSON, nullable=False, default=dict)  # {label: amount}
    deductions = Column(JSON, nullable=False, default=dict)
    effective_from = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)


class PayslipStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"


class Payslip(TenantBase):
    __tablename__ = "payslips"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "period", name="uq_payslip_user_period",
        ),
        Index("ix_payslip_period", "tenant_id", "period"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    period = Column(String(7), nullable=False)  # "2026-06"
    basic = Column(Numeric(12, 2), nullable=False, default=0)
    hra = Column(Numeric(12, 2), nullable=False, default=0)
    other_earnings = Column(Numeric(12, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(12, 2), nullable=False, default=0)
    net_pay = Column(Numeric(12, 2), nullable=False, default=0)
    breakdown = Column(JSON, nullable=True)  # snapshot of every line
    status = Column(
        String(12), nullable=False, default=PayslipStatus.DRAFT.value,
    )
    paid_on = Column(Date, nullable=True)


# ---------------------------------------------------------------------------
# 4. Inventory / Stores — items + movements
# ---------------------------------------------------------------------------


class InventoryItem(TenantBase):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_inv_item_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)
    name = Column(String(180), nullable=False)
    category = Column(String(80), nullable=True)  # furniture / lab / sports
    unit = Column(String(20), nullable=False, default="pcs")
    on_hand = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=0)
    unit_cost = Column(Numeric(12, 2), nullable=False, default=0)
    location = Column(String(80), nullable=True)
    notes = Column(Text, nullable=True)


class InventoryMovementKind(str, enum.Enum):
    IN = "in"
    OUT = "out"
    ADJUST = "adjust"


class InventoryMovement(TenantBase):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        Index("ix_inv_mov_item", "tenant_id", "item_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    item_id = Column(
        Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(
        String(10), nullable=False, default=InventoryMovementKind.IN.value,
    )
    quantity = Column(Integer, nullable=False)  # signed
    reference = Column(String(120), nullable=True)  # invoice / requisition
    occurred_on = Column(Date, nullable=False)
    by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 5. Visitor management
# ---------------------------------------------------------------------------


class VisitorLog(TenantBase):
    __tablename__ = "visitor_logs"
    __table_args__ = (
        Index("ix_visitor_tenant_in", "tenant_id", "checked_in_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    full_name = Column(String(180), nullable=False)
    phone = Column(String(20), nullable=True)
    company = Column(String(180), nullable=True)
    purpose = Column(String(180), nullable=True)
    host_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    id_proof_type = Column(String(40), nullable=True)  # aadhaar / dl / other
    id_proof_ref = Column(String(80), nullable=True)
    badge_no = Column(String(20), nullable=True)
    photo_url = Column(String(500), nullable=True)
    checked_in_at = Column(
        DateTime, nullable=False, server_default=func.now(),
    )
    checked_out_at = Column(DateTime, nullable=True)
    checked_in_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 6. Health / Infirmary — vaccinations, sick visits, allergy notes
# ---------------------------------------------------------------------------


class HealthRecordKind(str, enum.Enum):
    VISIT = "visit"
    VACCINATION = "vaccination"
    ALLERGY = "allergy"
    NOTE = "note"


class HealthRecord(TenantBase):
    __tablename__ = "health_records"
    __table_args__ = (
        Index("ix_health_student", "tenant_id", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False,
    )
    kind = Column(
        String(20), nullable=False, default=HealthRecordKind.VISIT.value,
    )
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    occurred_on = Column(Date, nullable=False)
    severity = Column(String(20), nullable=True)  # minor / moderate / major
    treatment = Column(Text, nullable=True)
    medication = Column(Text, nullable=True)
    follow_up_on = Column(Date, nullable=True)
    by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )


# ---------------------------------------------------------------------------
# 7. Certificates — templates + issued register
# ---------------------------------------------------------------------------


class CertificateTemplate(TenantBase):
    __tablename__ = "certificate_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_cert_tpl_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)  # bonafide / tc / character / conduct
    name = Column(String(120), nullable=False)
    body_html = Column(Text, nullable=False)  # mustache-style placeholders
    signatory_label = Column(String(120), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class IssuedCertificate(TenantBase):
    __tablename__ = "issued_certificates"
    __table_args__ = (
        Index("ix_issued_cert_student", "tenant_id", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    template_code = Column(String(40), nullable=False)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True,
    )
    for_name = Column(String(180), nullable=False)  # cached at issue-time
    reference_no = Column(String(40), nullable=False)
    issued_on = Column(Date, nullable=False)
    issued_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    rendered_body = Column(Text, nullable=False)  # HTML at issue-time
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 8. Discipline / Behaviour incidents
# ---------------------------------------------------------------------------


class DisciplineSeverity(str, enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class DisciplineIncident(TenantBase):
    __tablename__ = "discipline_incidents"
    __table_args__ = (
        Index("ix_discipline_student", "tenant_id", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False,
    )
    occurred_on = Column(Date, nullable=False)
    location = Column(String(80), nullable=True)
    severity = Column(
        String(12), nullable=False, default=DisciplineSeverity.MINOR.value,
    )
    headline = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    action_taken = Column(Text, nullable=True)
    reported_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    parent_informed = Column(Boolean, nullable=False, default=False)


# ---------------------------------------------------------------------------
# 9. Notice board — static bulletins (distinct from push announcements)
# ---------------------------------------------------------------------------


class NoticeAudience(str, enum.Enum):
    ALL = "all"
    STAFF = "staff"
    PARENTS = "parents"
    STUDENTS = "students"


class Notice(TenantBase):
    __tablename__ = "notices"
    __table_args__ = (
        Index("ix_notice_pub", "tenant_id", "published_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    title = Column(String(180), nullable=False)
    body = Column(Text, nullable=False)
    audience = Column(
        String(20), nullable=False, default=NoticeAudience.ALL.value,
    )
    is_pinned = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    attachments = Column(JSON, nullable=False, default=list)  # [{name, url}]
    # Particular people inside the audience who should see it. Empty /
    # NULL = everyone in the audience bucket.
    recipient_user_ids = Column(JSON, nullable=True)
    author_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )


# ---------------------------------------------------------------------------
# 10. Alumni directory
# ---------------------------------------------------------------------------


class Alumnus(TenantBase):
    __tablename__ = "alumni"
    __table_args__ = (
        Index("ix_alumni_year", "tenant_id", "graduation_year"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True,
    )
    full_name = Column(String(180), nullable=False)
    graduation_year = Column(Integer, nullable=False)
    current_role = Column(String(180), nullable=True)
    current_company = Column(String(180), nullable=True)
    email = Column(String(180), nullable=True)
    phone = Column(String(20), nullable=True)
    city = Column(String(80), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 11. Sports & clubs — houses + events
# ---------------------------------------------------------------------------


class SportsHouse(TenantBase):
    __tablename__ = "sports_houses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_sports_house_name"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    name = Column(String(80), nullable=False)  # Red, Blue, Green, Yellow ...
    color = Column(String(20), nullable=True)  # hex
    motto = Column(String(180), nullable=True)
    captain_student_id = Column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True,
    )
    points = Column(Integer, nullable=False, default=0)


class SportsEventKind(str, enum.Enum):
    TOURNAMENT = "tournament"
    MATCH = "match"
    PRACTICE = "practice"
    ANNUAL_DAY = "annual_day"
    CLUB = "club"


class SportsEvent(TenantBase):
    __tablename__ = "sports_events"
    __table_args__ = (
        Index("ix_sports_event_date", "tenant_id", "starts_on"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    name = Column(String(180), nullable=False)
    kind = Column(
        String(20), nullable=False, default=SportsEventKind.TOURNAMENT.value,
    )
    sport = Column(String(80), nullable=True)  # cricket, football, chess...
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=True)
    venue = Column(String(120), nullable=True)
    winner_house_id = Column(
        Integer, ForeignKey("sports_houses.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
