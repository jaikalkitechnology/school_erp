"""Audit log of every administrative action.

Super Admin actions and (later) sensitive school-admin actions land here so
support + compliance can answer "who changed what, when, from where".
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
)

from app.database import TenantBase


class AuditLog(TenantBase):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_actor", "actor_user_id"),
        Index("ix_audit_target", "target_type", "target_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_email = Column(String(180), nullable=True)
    actor_role = Column(String(40), nullable=True)
    action = Column(String(80), nullable=False)  # e.g. "tenant.create", "plan.update"
    target_type = Column(String(40), nullable=True)
    target_id = Column(Integer, nullable=True)
    summary = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
