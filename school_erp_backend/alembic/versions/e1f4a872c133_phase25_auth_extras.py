"""Phase 25: password reset OTPs + user device tokens.

Revision ID: e1f4a872c133
Revises: c9e21f4b7a05
Create Date: 2026-06-20 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f4a872c133"
down_revision: Union[str, None] = "c9e21f4b7a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_otps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column(
            "delivery_channel", sa.String(16), nullable=False,
            server_default="sms",
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default="0",
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
            ["user_id"], ["users.id"], ondelete="CASCADE",
        ),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_pwd_otp_user", "password_reset_otps",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_pwd_otp_active", "password_reset_otps",
        ["user_id", "consumed_at", "expires_at"],
    )

    op.create_table(
        "user_devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fcm_token", sa.String(255), nullable=False),
        sa.Column(
            "platform", sa.String(16), nullable=False,
            server_default="android",
        ),
        sa.Column("app_version", sa.String(32), nullable=True),
        sa.Column("device_label", sa.String(128), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true(),
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
            ["user_id"], ["users.id"], ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "fcm_token", name="uq_user_device_token"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_user_device_user", "user_devices",
        ["tenant_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_device_user", table_name="user_devices")
    op.drop_table("user_devices")
    op.drop_index("ix_pwd_otp_active", table_name="password_reset_otps")
    op.drop_index("ix_pwd_otp_user", table_name="password_reset_otps")
    op.drop_table("password_reset_otps")
