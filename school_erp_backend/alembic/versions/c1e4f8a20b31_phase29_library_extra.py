"""Phase 29 — library extra tables (shelves, settings, audit, verification).

Revision ID: c1e4f8a20b31
Revises: b7d3e9a10c44
Create Date: 2026-09-03
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "c1e4f8a20b31"
down_revision: Union[str, None] = "b7d3e9a10c44"
branch_labels = None
depends_on = None


def _tenant_cols():
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(), server_onupdate=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "library_shelves",
        *_tenant_cols(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("section", sa.String(120), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="40"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_shelves_code"),
        sa.Index("ix_library_shelves_tenant", "tenant_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "library_settings",
        *_tenant_cols(),
        sa.Column("loan_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("fine_per_day", sa.Numeric(7, 2), nullable=False, server_default="1"),
        sa.Column("max_books_per_borrower", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("reservation_expiry_days", sa.Integer(), nullable=False, server_default="3"),
        sa.UniqueConstraint("tenant_id", name="uq_library_settings_tenant"),
        sa.Index("ix_library_settings_tenant", "tenant_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "library_audit_logs",
        *_tenant_cols(),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(255), nullable=True),
        sa.Column(
            "actor_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Index("ix_library_audit_created", "tenant_id", "created_at"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "library_verification_sessions",
        *_tenant_cols(),
        sa.Column("status", sa.String(15), nullable=False, server_default="open"),
        sa.Column(
            "started_by_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Index("ix_library_verif_sessions_tenant", "tenant_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "library_verification_scans",
        *_tenant_cols(),
        sa.Column(
            "session_id", sa.Integer(),
            sa.ForeignKey("library_verification_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "copy_id", sa.Integer(),
            sa.ForeignKey("library_copies.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("barcode", sa.String(60), nullable=False),
        sa.Column("found", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("scanned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "session_id", "copy_id", name="uq_verif_scan"),
        sa.Index("ix_verif_scan_session", "session_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("library_verification_scans")
    op.drop_table("library_verification_sessions")
    op.drop_table("library_audit_logs")
    op.drop_table("library_settings")
    op.drop_table("library_shelves")
