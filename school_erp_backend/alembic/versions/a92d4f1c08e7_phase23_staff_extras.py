"""Phase 23: staff_leaves + behaviour_notes for the teacher app.

Revision ID: a92d4f1c08e7
Revises: f6567bd9b857
Create Date: 2026-06-15 11:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a92d4f1c08e7"
down_revision: Union[str, None] = "f6567bd9b857"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_leaves",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False, server_default="casual"),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending",
        ),
        sa.Column("decision_remarks", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"], ["users.id"], ondelete="SET NULL",
        ),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_staff_leaves_tenant_user_status",
        "staff_leaves",
        ["tenant_id", "user_id", "status"],
    )

    op.create_table(
        "behaviour_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column(
            "kind", sa.String(20), nullable=False, server_default="neutral",
        ),
        sa.Column("headline", sa.String(180), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "visible_to_parent", sa.Boolean(), nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_user_id"], ["users.id"], ondelete="SET NULL",
        ),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_behaviour_notes_tenant_student",
        "behaviour_notes",
        ["tenant_id", "student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_behaviour_notes_tenant_student", table_name="behaviour_notes")
    op.drop_table("behaviour_notes")
    op.drop_index("ix_staff_leaves_tenant_user_status", table_name="staff_leaves")
    op.drop_table("staff_leaves")
