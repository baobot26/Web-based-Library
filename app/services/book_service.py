from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError
from app.infrastructure.models import BookModel, ChapterModel, UserModel


def list_books(session: Session, q: str | None, page: int, size: int) -> dict:
    """Return one page of non-deleted books, newest first."""
    chapter_count = (
        select(func.count(ChapterModel.id))
        .where(ChapterModel.book_id == BookModel.id, ChapterModel.deleted_at.is_(None))
        .correlate(BookModel)
        .scalar_subquery()
    )
    stmt = (
        select(BookModel, UserModel.name, chapter_count.label("chapter_count"))
        .join(UserModel, BookModel.uploader_id == UserModel.id)
        .where(BookModel.deleted_at.is_(None))
    )
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(BookModel.title.ilike(f"%{escaped}%", escape="\\"))

    total = session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    rows = session.execute(
        stmt.order_by(BookModel.created_at.desc(), BookModel.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    return {
        "items": [
            {
                "id": book.id,
                "title": book.title,
                "description": book.description,
                "uploader_id": book.uploader_id,
                "uploader_name": uploader_name,
                "chapter_count": count,
                "created_at": book.created_at,
            }
            for book, uploader_name, count in rows
        ],
        "page": page,
        "size": size,
        "total": total,
    }


def get_book(session: Session, book_id: int) -> dict:
    """Return one non-deleted book with its uploader name and live chapters."""
    row = session.execute(
        select(BookModel, UserModel.name)
        .join(UserModel, BookModel.uploader_id == UserModel.id)
        .where(BookModel.id == book_id, BookModel.deleted_at.is_(None))
    ).one_or_none()
    if row is None:
        raise NotFoundError("BOOK_NOT_FOUND", f"Book {book_id} does not exist")
    book, uploader_name = row

    chapters = session.execute(
        select(ChapterModel.number, ChapterModel.title)
        .where(ChapterModel.book_id == book_id, ChapterModel.deleted_at.is_(None))
        .order_by(ChapterModel.number)
    ).all()

    return {
        "id": book.id,
        "title": book.title,
        "description": book.description,
        "uploader_id": book.uploader_id,
        "uploader_name": uploader_name,
        "created_at": book.created_at,
        "chapters": [{"number": number, "title": title} for number, title in chapters],
    }


def get_chapter(session: Session, book_id: int, number: int) -> dict:
    """Return one live chapter after verifying its live book exists."""
    book_exists = session.execute(
        select(BookModel.id).where(
            BookModel.id == book_id,
            BookModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if book_exists is None:
        raise NotFoundError("BOOK_NOT_FOUND", f"Book {book_id} does not exist")

    chapter = session.execute(
        select(ChapterModel).where(
            ChapterModel.book_id == book_id,
            ChapterModel.number == number,
            ChapterModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if chapter is None:
        raise NotFoundError(
            "CHAPTER_NOT_FOUND",
            f"Chapter {number} of book {book_id} does not exist",
        )

    return {
        "book_id": chapter.book_id,
        "number": chapter.number,
        "title": chapter.title,
        "content": chapter.content,
    }
