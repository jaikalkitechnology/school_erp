"""Library schemas (Phase 17)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.library import (
    BorrowerKind,
    CopyStatus,
    LoanStatus,
    ReservationStatus,
)


# ---- Books -----------------------------------------------------------------


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    isbn: Optional[str]
    title: str
    author: Optional[str]
    publisher: Optional[str]
    edition: Optional[str]
    category: Optional[str]
    language: Optional[str]
    cover_path: Optional[str]
    description: Optional[str]
    default_fine_per_day: Decimal
    default_loan_days: int


class BookWrite(BaseModel):
    isbn: Optional[str] = None
    title: str = Field(min_length=1, max_length=200)
    author: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = "english"
    cover_path: Optional[str] = None
    description: Optional[str] = None
    default_fine_per_day: Decimal = Field(default=Decimal("0"), ge=0)
    default_loan_days: int = Field(default=14, gt=0)


class BookWithStock(BookRead):
    total_copies: int
    available_copies: int


# ---- Copies ----------------------------------------------------------------


class CopyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    barcode: str
    accession_number: Optional[str]
    status: CopyStatus
    notes: Optional[str]


class CopyWrite(BaseModel):
    barcode: str = Field(min_length=1, max_length=60)
    accession_number: Optional[str] = None
    notes: Optional[str] = None


class CopyBulkAdd(BaseModel):
    count: int = Field(ge=1, le=200)
    accession_prefix: Optional[str] = None
    barcode_prefix: Optional[str] = None


# ---- Loans -----------------------------------------------------------------


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    copy_id: int
    book_id: int
    borrower_kind: BorrowerKind
    borrower_id: int
    issued_on: date
    due_on: date
    returned_on: Optional[date]
    status: LoanStatus
    fine_amount: Decimal
    fine_paid: Decimal


class IssueRequest(BaseModel):
    copy_id: int
    borrower_kind: BorrowerKind
    borrower_id: int
    loan_days: Optional[int] = None  # falls back to book default


class ReturnRequest(BaseModel):
    loan_id: int
    on_date: Optional[date] = None  # for back-dating; defaults to today
    fine_paid: Optional[Decimal] = None
    mark_lost: bool = False


# ---- Reservations ----------------------------------------------------------


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    borrower_kind: BorrowerKind
    borrower_id: int
    requested_at: datetime
    ready_at: Optional[datetime]
    fulfilled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    status: ReservationStatus


class ReservationWrite(BaseModel):
    book_id: int
    borrower_kind: BorrowerKind
    borrower_id: int


# ---- Reports ---------------------------------------------------------------


class CategoryCount(BaseModel):
    category: Optional[str]
    books: int
    copies: int


class LibraryReports(BaseModel):
    total_books: int
    total_copies: int
    issued: int
    overdue: int
    available: int
    fines_outstanding: Decimal
    by_category: List[CategoryCount]


class ParentLibraryRow(BaseModel):
    loan_id: int
    book_id: int
    book_title: str
    issued_on: date
    due_on: date
    returned_on: Optional[date]
    status: LoanStatus
    fine_amount: Decimal


class ParentLibrary(BaseModel):
    student_id: int
    rows: List[ParentLibraryRow]
