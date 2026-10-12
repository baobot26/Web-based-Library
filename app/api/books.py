from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.schemas import BookDetail, BookListResponse, ChapterDetail
from app.infrastructure.db import get_session
from app.services import book_service

router = APIRouter(prefix="/books", tags=["books"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=BookListResponse)
def list_books(
    session: SessionDep,
    q: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    """Browse/search books. Newest first, soft-deleted hidden, guests allowed."""
    return book_service.list_books(session, q, page, size)


@router.get("/{book_id}", response_model=BookDetail)
def get_book(book_id: int, session: SessionDep) -> dict:
    """Book info with its chapter list. Guests allowed."""
    return book_service.get_book(session, book_id)


@router.get("/{book_id}/chapters/{number}", response_model=ChapterDetail)
def get_chapter(
    book_id: int,
    number: Annotated[int, Path(ge=1)],
    session: SessionDep,
) -> dict:
    """Read one live chapter. Guests allowed."""
    return book_service.get_chapter(session, book_id, number)
