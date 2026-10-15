from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUserId
from app.api.schemas import CreateBookmarkRequest, CreateBookmarkResponse
from app.infrastructure.db import get_session
from app.services import book_service

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=CreateBookmarkResponse, status_code=201)
def create_bookmark(
    request: CreateBookmarkRequest,
    session: SessionDep,
    user_id: CurrentUserId,
) -> CreateBookmarkResponse:
    """Create a bookmark for a chapter of a book. Logged in required."""
    return book_service.create_bookmark(session, user_id, request.book_id, request.chapter_number)
    
@router.get("", response_model=list[CreateBookmarkResponse])
def get_bookmarks(
    session: SessionDep,
    user_id: CurrentUserId,
) -> list[CreateBookmarkResponse]:
    """Get all bookmarks of an user. Logged in required."""
    return book_service.get_bookmarks(session, user_id)

@router.get("/{book_id}", response_model=list[CreateBookmarkResponse])
def get_bookmarks_by_book(
    book_id: int,
    session: SessionDep,
    user_id: CurrentUserId,
) -> list[CreateBookmarkResponse]:
    """Get all bookmarks for a specific book of an user. Logged in required."""
    return book_service.get_bookmarks(session, user_id, book_id)
