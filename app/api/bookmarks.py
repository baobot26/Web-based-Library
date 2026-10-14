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
    """Create a bookmark for a chapter of a book. Only logged in users."""
    return book_service.create_bookmark(
        session,
        user_id,
        request.book_id,
        request.chapter_number,
    )