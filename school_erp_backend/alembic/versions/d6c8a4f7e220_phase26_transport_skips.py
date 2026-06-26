"""Phase 26: trip_skips for parent "not coming today" opt-out.

Revision ID: d6c8a4f7e220
Revises: e1f4a872c133
Create Date: 2026-06-27 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6c8a4f7e220"
down_revision: Union[str, None] = "e1f4a872c133"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transport_trip_skips",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        # The skip is dated. Parent can opt-out for any future date —
        # we don't tie this to a trip row because the trip may not exist
        # yet at the moment the parent toggles "not coming today".
        sa.Column("skip_date", sa.Date(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False, server_default="pickup"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "student_id", "skip_date", "direction",
            name="uq_trip_skip_unique",
        ),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_trip_skips_date_student",
        "transport_trip_skips",
        ["skip_date", "student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_trip_skips_date_student", table_name="transport_trip_skips")
    op.drop_table("transport_trip_skips")
