"""Add users.google_sub for Google Sign-In.

Revision ID: b7d3e9a10c44
Revises: a5c2d9e11f28
Create Date: 2026-07-14 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d3e9a10c44"
down_revision: Union[str, None] = "a5c2d9e11f28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_users_tenant_google_sub", "users", ["tenant_id", "google_sub"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_tenant_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
