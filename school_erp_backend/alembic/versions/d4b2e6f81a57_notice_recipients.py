"""Notices can target particular people inside their audience.

Revision ID: d4b2e6f81a57
Revises: c1e4f8a20b31
Create Date: 2026-10-22
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4b2e6f81a57"
down_revision: Union[str, None] = "c1e4f8a20b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL / empty = everyone in the notice's audience.
    op.add_column("notices", sa.Column("recipient_user_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("notices", "recipient_user_ids")
