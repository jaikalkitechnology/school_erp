"""Library endpoints (Phase 17)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.library import BorrowerKind
from app.models.parent import Parent, ParentChildMapping
from app.schemas.library import (
    BookRead,
    BookWithStock,
    BookWrite,
    CopyBulkAdd,
    CopyRead,
    CopyWrite,
    IssueRequest,
    LibraryReports,
    LoanRead,
    ParentLibrary,
    ParentLibraryRow,
    ReservationRead,
    ReservationWrite,
    ReturnRequest,
)
from app.services.library import (
    add_copies_bulk,
    add_copy,
    book_stock,
    cancel_reservation,
    create_book,
    create_reservation,
    delete_book,
    issue_loan,
    list_books,
    list_copies,
    list_loans,
    list_reservations,
    mark_overdue,
    parent_child_loans,
    reports,
    return_loan,
    update_book,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_librarian = require_roles(
    "school_admin", "principal", "vice_principal", "librarian", "coordinator",
)
_reader = require_roles(
    "school_admin", "principal", "vice_principal", "librarian", "coordinator",
    "class_teacher", "subject_teacher",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/library",
    tags=["school-admin"],
    dependencies=[Depends(_reader)],
)


# ---- Books -----------------------------------------------------------------


@router.get("/books", response_model=list[BookWithStock])
async def list_books_route(
    q: Optional[str] = None,
    category: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    books = await list_books(session, q=q, category=category)
    stocks = await book_stock(session, [b.id for b in books])
    return [
        {
            **{c.name: getattr(b, c.name) for c in b.__table__.columns},
            "total_copies": stocks.get(b.id, {}).get("total", 0),
            "available_copies": stocks.get(b.id, {}).get("available", 0),
        }
        for b in books
    ]


@router.post("/books", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book_route(
    payload: BookWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_book(session, principal.tenant_id, payload)


@router.patch("/books/{book_id}", response_model=BookRead)
async def update_book_route(
    book_id: int,
    payload: BookWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_book(session, book_id, payload)


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book_route(
    book_id: int,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Delete a book from the catalogue. The service blocks the
    delete if any copy is still on active loan — so no data-loss
    risk when the librarian mis-clicks. School admins used to be
    required; librarians run the day-to-day catalogue so they now
    own it too."""
    await delete_book(session, book_id)


# ---- Categories (free-text on Book.category) -------------------------------


@router.post("/categories/rename")
async def rename_category_route(
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Rename a category across every book that currently carries
    it. Payload: ``{"from": "Sci-Fi", "to": "Science Fiction"}``.

    Categories aren't a first-class table — they're a free-text
    string on ``Book.category``. Rename = bulk UPDATE. The response
    reports how many books were touched so the librarian sees the
    scope of the change."""
    from app.models.library import Book

    source = (payload.get("from") or "").strip()
    target = (payload.get("to") or "").strip()
    if not source or not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'from' and 'to' are required",
        )
    if source == target:
        return {"updated": 0}

    books = list(
        (
            await session.execute(
                select(Book).where(Book.category == source)
            )
        ).scalars().all()
    )
    for b in books:
        b.category = target
    await session.commit()
    return {"updated": len(books), "from": source, "to": target}


@router.delete("/categories/{name}", status_code=status.HTTP_200_OK)
async def delete_category_route(
    name: str,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Delete a category by clearing it off every book that carries
    it (books survive; they just become "Uncategorised"). Returns
    the count of books touched."""
    from app.models.library import Book

    name = (name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category name required",
        )
    books = list(
        (
            await session.execute(
                select(Book).where(Book.category == name)
            )
        ).scalars().all()
    )
    for b in books:
        b.category = None
    await session.commit()
    return {"cleared": len(books), "category": name}


# ---- Copies ----------------------------------------------------------------


@router.get("/books/{book_id}/copies", response_model=list[CopyRead])
async def list_copies_route(
    book_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_copies(session, book_id)


@router.post(
    "/books/{book_id}/copies",
    response_model=CopyRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_copy_route(
    book_id: int,
    payload: CopyWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_copy(session, principal.tenant_id, book_id, payload)


@router.post("/books/{book_id}/copies/bulk", response_model=list[CopyRead])
async def add_copies_bulk_route(
    book_id: int,
    payload: CopyBulkAdd,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_copies_bulk(session, principal.tenant_id, book_id, payload)


# ---- Circulation ----------------------------------------------------------


@router.post("/issue", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def issue_route(
    payload: IssueRequest,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await issue_loan(session, principal.tenant_id, principal.user_id, payload)


@router.post("/return", response_model=LoanRead)
async def return_route(
    payload: ReturnRequest,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await return_loan(session, principal.user_id, payload)


@router.get("/loans", response_model=list[LoanRead])
async def list_loans_route(
    status_filter: Optional[str] = None,
    borrower_kind: Optional[BorrowerKind] = None,
    borrower_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_loans(
        session,
        status_filter=status_filter,
        borrower_kind=borrower_kind,
        borrower_id=borrower_id,
    )


@router.post("/sweep-overdue")
async def sweep_overdue_route(
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    n = await mark_overdue(session)
    return {"marked_overdue": n}


# ---- Reservations ---------------------------------------------------------


@router.get("/reservations", response_model=list[ReservationRead])
async def list_reservations_route(
    status_filter: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_reservations(session, status_filter=status_filter)


@router.post(
    "/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation_route(
    payload: ReservationWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_reservation(session, principal.tenant_id, payload)


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation_route(
    reservation_id: int,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await cancel_reservation(session, reservation_id)


# ---- Reports ---------------------------------------------------------------


@router.get("/reports", response_model=LibraryReports)
async def reports_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await reports(session)


# ---- Parent view -----------------------------------------------------------


parent_router = APIRouter(
    prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)]
)


@parent_router.get(
    "/children/{student_id}/library", response_model=ParentLibrary
)
async def parent_library_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    rows = await parent_child_loans(session, student_id)
    return ParentLibrary(
        student_id=student_id,
        rows=[ParentLibraryRow(**r) for r in rows],
    )


@parent_router.get("/library/catalog", response_model=list[BookWithStock])
async def parent_library_catalog(
    q: Optional[str] = None,
    category: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Read-only book search for parents. Same search/filter shape as the
    librarian endpoint but without write actions — parents shouldn't be
    able to add/edit/delete books, and circulation still flows through
    the librarian-only POST /issue route."""
    books = await list_books(session, q=q, category=category)
    stocks = await book_stock(session, [b.id for b in books])
    return [
        {
            **{c.name: getattr(b, c.name) for c in b.__table__.columns},
            "total_copies": stocks.get(b.id, {}).get("total", 0),
            "available_copies": stocks.get(b.id, {}).get("available", 0),
        }
        for b in books
    ]
