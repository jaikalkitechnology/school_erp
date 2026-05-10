"""Report card schemas (Phase 16)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.report_cards import ReportCardStatus, TemplateBoard


# ---- Templates -------------------------------------------------------------


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    board: TemplateBoard
    layout: dict
    is_default: bool


class TemplateWrite(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    board: TemplateBoard = TemplateBoard.CBSE
    layout: dict = Field(default_factory=dict)
    is_default: bool = False


# ---- Co-curricular + remarks ----------------------------------------------


class CoCurricularWrite(BaseModel):
    student_id: int
    area: str = Field(min_length=1, max_length=60)
    grade: str = Field(min_length=1, max_length=10)
    remarks: Optional[str] = None


class CoCurricularRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_id: int
    student_id: int
    area: str
    grade: str
    remarks: Optional[str]


class RemarkWrite(BaseModel):
    student_id: int
    teacher_remark: Optional[str] = None
    principal_remark: Optional[str] = None


class RemarkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_id: int
    student_id: int
    teacher_remark: Optional[str]
    principal_remark: Optional[str]


# ---- Generation ------------------------------------------------------------


class GenerateRequest(BaseModel):
    exam_id: int
    section_id: int
    template_id: Optional[int] = None
    publish: bool = False


class GenerateResult(BaseModel):
    generated: int
    skipped: int
    skipped_reasons: List[str] = Field(default_factory=list)


class ReportCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_id: int
    student_id: int
    template_id: Optional[int]
    status: ReportCardStatus
    total_marks: Optional[Decimal]
    obtained_marks: Optional[Decimal]
    percentage: Optional[Decimal]
    overall_grade: Optional[str]
    rank_in_section: Optional[int]
    snapshot: dict
    pdf_path: Optional[str]
    generated_at: Optional[datetime]
    published_at: Optional[datetime]


class ParentReportCardRow(BaseModel):
    report_card_id: int
    exam_id: int
    exam_name: str
    status: ReportCardStatus
    percentage: Optional[Decimal]
    overall_grade: Optional[str]
    rank_in_section: Optional[int]
    pdf_url: str
    published_at: Optional[datetime]


class ParentReportCards(BaseModel):
    student_id: int
    rows: List[ParentReportCardRow]
