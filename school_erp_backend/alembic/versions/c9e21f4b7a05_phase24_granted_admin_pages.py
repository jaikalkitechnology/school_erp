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
    """Add users.granted_admin_pages JSON column.

    MySQL refuses ``DEFAULT '[]'`` on a JSON column ("BLOB, TEXT, GEOMETRY
    or JSON column can't have a default value" — error 1101). We work
    around that with a three-step migration that works on both MySQL
    and Postgres:

    1. Add the column nullable.
    2. Backfill an empty JSON array via ``JSON_ARRAY()`` (MySQL) /
       ``'[]'::jsonb`` cast (Postgres).
    3. Flip the column to NOT NULL.

    Going forward, new rows go through the SQLAlchemy ``default=list``
    on the model column, so we don't need a real DB-side default.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column(
        "users",
        sa.Column("granted_admin_pages", sa.JSON(), nullable=True),
    )

    if dialect == "mysql":
        op.execute(
            "UPDATE users SET granted_admin_pages = JSON_ARRAY() "
            "WHERE granted_admin_pages IS NULL"
        )
    else:
        # Postgres / SQLite (dev).
        op.execute(
            "UPDATE users SET granted_admin_pages = '[]' "
            "WHERE granted_admin_pages IS NULL"
        )

    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "granted_admin_pages",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    op.drop_column("users", "granted_admin_pages")
