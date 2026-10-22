"""Announcements can target particular people inside their audience.

Revision ID: e5c3f7a92b68
Revises: d4b2e6f81a57
Create Date: 2026-10-22
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5c3f7a92b68"
down_revision: Union[str, None] = "d4b2e6f81a57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL / empty = everyone in the announcement's audience.
    op.add_column("announcements", sa.Column("recipient_user_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("announcements", "recipient_user_ids")
