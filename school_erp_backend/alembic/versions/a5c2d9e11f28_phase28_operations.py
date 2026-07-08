"""Phase 28: operations modules — Admissions, Finance, Payroll, Inventory,
Visitor, Health, Certificates, Discipline, Notices, Alumni, Sports.

Revision ID: a5c2d9e11f28
Revises: d6c8a4f7e220
Create Date: 2026-07-08 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5c2d9e11f28"
down_revision: Union[str, None] = "d6c8a4f7e220"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_cols():
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    # ---- Admissions ----------------------------------------------------
    op.create_table(
        "admission_inquiries",
        *_tenant_cols(),
        sa.Column("child_full_name", sa.String(180), nullable=False),
        sa.Column("child_dob", sa.Date(), nullable=True),
        sa.Column("class_applying_for", sa.String(40), nullable=True),
        sa.Column("parent_name", sa.String(180), nullable=True),
        sa.Column("parent_phone", sa.String(20), nullable=True),
        sa.Column("parent_email", sa.String(180), nullable=True),
        sa.Column("source", sa.String(40), nullable=True),
        sa.Column(
            "stage", sa.String(20), nullable=False, server_default="enquiry",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column("test_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "handled_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Index("ix_adm_inq_tenant_stage", "tenant_id", "stage"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Vendors + Expenses --------------------------------------------
    op.create_table(
        "vendors",
        *_tenant_cols(),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("contact_person", sa.String(120), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(180), nullable=True),
        sa.Column("gst_number", sa.String(40), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_vendor_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "expenses",
        *_tenant_cols(),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("vendors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column("paid_from", sa.String(40), nullable=True),
        sa.Column("invoice_ref", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(12), nullable=False, server_default="pending",
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Index("ix_expenses_tenant_date", "tenant_id", "spent_on"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Salary structure + Payslip ------------------------------------
    op.create_table(
        "salary_structures",
        *_tenant_cols(),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("basic", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("hra", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("allowances", sa.JSON(), nullable=False),
        sa.Column("deductions", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Index("ix_salary_user", "tenant_id", "user_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "payslips",
        *_tenant_cols(),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("basic", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("hra", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "other_earnings", sa.Numeric(12, 2), nullable=False, server_default="0",
        ),
        sa.Column(
            "total_deductions", sa.Numeric(12, 2), nullable=False, server_default="0",
        ),
        sa.Column("net_pay", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.Column(
            "status", sa.String(12), nullable=False, server_default="draft",
        ),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "user_id", "period", name="uq_payslip_user_period",
        ),
        sa.Index("ix_payslip_period", "tenant_id", "period"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Inventory -----------------------------------------------------
    op.create_table(
        "inventory_items",
        *_tenant_cols(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("location", sa.String(80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_inv_item_code"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "inventory_movements",
        *_tenant_cols(),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("inventory_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(10), nullable=False, server_default="in"),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column(
            "by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Index("ix_inv_mov_item", "tenant_id", "item_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Visitors ------------------------------------------------------
    op.create_table(
        "visitor_logs",
        *_tenant_cols(),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("company", sa.String(180), nullable=True),
        sa.Column("purpose", sa.String(180), nullable=True),
        sa.Column(
            "host_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("id_proof_type", sa.String(40), nullable=True),
        sa.Column("id_proof_ref", sa.String(80), nullable=True),
        sa.Column("badge_no", sa.String(20), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column(
            "checked_in_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("checked_out_at", sa.DateTime(), nullable=True),
        sa.Column(
            "checked_in_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Index("ix_visitor_tenant_in", "tenant_id", "checked_in_at"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Health --------------------------------------------------------
    op.create_table(
        "health_records",
        *_tenant_cols(),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False, server_default="visit"),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("medication", sa.Text(), nullable=True),
        sa.Column("follow_up_on", sa.Date(), nullable=True),
        sa.Column(
            "by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Index("ix_health_student", "tenant_id", "student_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Certificates --------------------------------------------------
    op.create_table(
        "certificate_templates",
        *_tenant_cols(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("signatory_label", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("tenant_id", "code", name="uq_cert_tpl_code"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "issued_certificates",
        *_tenant_cols(),
        sa.Column("template_code", sa.String(40), nullable=False),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("for_name", sa.String(180), nullable=False),
        sa.Column("reference_no", sa.String(40), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column(
            "issued_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rendered_body", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Index("ix_issued_cert_student", "tenant_id", "student_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Discipline ----------------------------------------------------
    op.create_table(
        "discipline_incidents",
        *_tenant_cols(),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("location", sa.String(80), nullable=True),
        sa.Column("severity", sa.String(12), nullable=False, server_default="minor"),
        sa.Column("headline", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column(
            "reported_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_informed", sa.Boolean(), nullable=False, server_default=sa.text("0"),
        ),
        sa.Index("ix_discipline_student", "tenant_id", "student_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Notice board --------------------------------------------------
    op.create_table(
        "notices",
        *_tenant_cols(),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("audience", sa.String(20), nullable=False, server_default="all"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=False),
        sa.Column(
            "author_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Index("ix_notice_pub", "tenant_id", "published_at"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Alumni --------------------------------------------------------
    op.create_table(
        "alumni",
        *_tenant_cols(),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("graduation_year", sa.Integer(), nullable=False),
        sa.Column("current_role", sa.String(180), nullable=True),
        sa.Column("current_company", sa.String(180), nullable=True),
        sa.Column("email", sa.String(180), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Index("ix_alumni_year", "tenant_id", "graduation_year"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # ---- Sports --------------------------------------------------------
    op.create_table(
        "sports_houses",
        *_tenant_cols(),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("motto", sa.String(180), nullable=True),
        sa.Column(
            "captain_student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_sports_house_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "sports_events",
        *_tenant_cols(),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column(
            "kind", sa.String(20), nullable=False, server_default="tournament",
        ),
        sa.Column("sport", sa.String(80), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("venue", sa.String(120), nullable=True),
        sa.Column(
            "winner_house_id",
            sa.Integer(),
            sa.ForeignKey("sports_houses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Index("ix_sports_event_date", "tenant_id", "starts_on"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    for tbl in [
        "sports_events",
        "sports_houses",
        "alumni",
        "notices",
        "discipline_incidents",
        "issued_certificates",
        "certificate_templates",
        "health_records",
        "visitor_logs",
        "inventory_movements",
        "inventory_items",
        "payslips",
        "salary_structures",
        "expenses",
        "vendors",
        "admission_inquiries",
    ]:
        op.drop_table(tbl)
