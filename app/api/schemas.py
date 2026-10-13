from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


def _iso_utc_z(value: datetime) -> str:
    """Render a datetime as ISO 8601 UTC with a Z suffix."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


Timestamp = Annotated[datetime, PlainSerializer(_iso_utc_z, return_type=str)]


class BookListItem(BaseModel):
    id: int
    title: str
    description: str
    uploader_id: int
    uploader_name: str
    chapter_count: int
    created_at: Timestamp


class BookListResponse(BaseModel):
    items: list[BookListItem]
    page: int
    size: int
    total: int


class ChapterRef(BaseModel):
    number: int
    title: str


class BookDetail(BaseModel):
    id: int
    title: str
    description: str
    uploader_id: int
    uploader_name: str
    created_at: Timestamp
    chapters: list[ChapterRef]


class ChapterDetail(BaseModel):
    book_id: int
    number: int
    title: str
    content: str
