"""Phase 24: granted_admin_pages JSON on users.

Revision ID: c9e21f4b7a05
Revises: a92d4f1c08e7
Create Date: 2026-06-16 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e21f4b7a05"
down_revision: Union[str, None] = "a92d4f1c08e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "granted_admin_pages",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "granted_admin_pages")
