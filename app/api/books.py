from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas import BookListResponse
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
