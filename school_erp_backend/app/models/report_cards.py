"""Report card entities (Phase 16)."""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.database import TenantBase


class TemplateBoard(str, enum.Enum):
    CBSE = "cbse"
    ICSE = "icse"
    STATE = "state"
    CUSTOM = "custom"


class ReportCardStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    PUBLISHED = "published"


class ReportCardTemplate(TenantBase):
    """Per-tenant template definition. ``layout`` carries:
        {
          "show_co_curricular": true,
          "show_attendance": true,
          "show_remarks": true,
          "header_lines": ["Annual Report"],
          "footer_text": "...",
          "co_curricular_areas": ["Discipline","Sports","Art"],
        }
    """

    __tablename__ = "report_card_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_rc_templates_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    board = Column(String(20), nullable=False, default=TemplateBoard.CBSE.value)
    layout = Column(JSON, nullable=False, default=dict)
    is_default = Column(Boolean, nullable=False, default=False)


class CoCurricularGrade(TenantBase):
    """Per-student per-exam co-curricular evaluation."""

    __tablename__ = "co_curricular_grades"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "exam_id", "student_id", "area",
            name="uq_co_curricular_unique",
        ),
        Index("ix_co_curricular_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    area = Column(String(60), nullable=False)
    grade = Column(String(10), nullable=False)
    remarks = Column(String(255), nullable=True)


class ReportCardRemark(TenantBase):
    """Class teacher / principal remarks."""

    __tablename__ = "report_card_remarks"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "exam_id", "student_id",
            name="uq_rc_remarks_unique",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    teacher_remark = Column(Text, nullable=True)
    principal_remark = Column(Text, nullable=True)


class ReportCard(TenantBase):
    """A generated card. ``snapshot`` stores the rendered JSON used by the PDF
    so a parent can always re-download the same card even if marks change."""

    __tablename__ = "report_cards"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "exam_id", "student_id",
            name="uq_report_card_unique",
        ),
        Index("ix_report_cards_exam", "exam_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(
        Integer,
        ForeignKey("report_card_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(15), nullable=False, default=ReportCardStatus.GENERATED.value)
    total_marks = Column(Numeric(8, 2), nullable=True)
    obtained_marks = Column(Numeric(8, 2), nullable=True)
    percentage = Column(Numeric(5, 2), nullable=True)
    overall_grade = Column(String(10), nullable=True)
    rank_in_section = Column(Integer, nullable=True)
    snapshot = Column(JSON, nullable=False, default=dict)
    pdf_path = Column(String(255), nullable=True)
    generated_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
