from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, PlainSerializer, field_validator


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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > 72:
            raise ValueError("must be at most 72 bytes")
        return value


class UserResponse(BaseModel):
    id: int
    email: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
