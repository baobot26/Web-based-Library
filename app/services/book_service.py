from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import ConflictError, NotFoundError
from app.infrastructure.models import BookmarkModel, BookModel, ChapterModel, UserModel


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


def create_bookmark(
    session: Session,
    user_id: int,
    book_id: int,
    chapter_number: int,
) -> dict:
    """Bookmark a chapter for user."""
    chapter = session.execute(
        select(ChapterModel, BookModel)
        .join(BookModel, ChapterModel.book_id == BookModel.id)
        .where(
            BookModel.id == book_id,
            BookModel.deleted_at.is_(None),
            ChapterModel.number == chapter_number,
            ChapterModel.deleted_at.is_(None),
        )
    ).one_or_none()
    if chapter is None:
        raise NotFoundError(
            "CHAPTER_NOT_FOUND",
            f"Chapter {chapter_number} of book {book_id} does not exist",
        )

    chapter_model, book_model = chapter
    existing = session.execute(
        select(BookmarkModel).where(
            BookmarkModel.user_id == user_id,
            BookmarkModel.chapter_id == chapter_model.id,
            BookmarkModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "BOOKMARK_EXISTS",
            f"Chapter {chapter_number} of book {book_id} is already bookmarked",
        )

    bookmark = session.execute(
        select(BookmarkModel)
        .where(
            BookmarkModel.user_id == user_id,
            BookmarkModel.chapter_id == chapter_model.id,
        )
        .order_by(BookmarkModel.id.desc())
    ).scalars().first()
    if bookmark is None:
        bookmark = BookmarkModel(
            user_id=user_id,
            chapter_id=chapter_model.id,
        )
        session.add(bookmark)
    else:
        bookmark.deleted_at = None

    session.commit()
    session.refresh(bookmark)
    return {
        "id": bookmark.id,
        "book_id": book_model.id,
        "book_title": book_model.title,
        "chapter_number": chapter_model.number,
        "chapter_title": chapter_model.title,
        "created_at": bookmark.created_at,
    }

def get_bookmarks(session: Session, user_id: int, book_id = None) -> list[dict]:
    """Return all bookmarks/filter by books for a user."""
    bookmarks = (
        select(BookmarkModel, ChapterModel, BookModel)
        .join(ChapterModel, BookmarkModel.chapter_id == ChapterModel.id)
        .join(BookModel, ChapterModel.book_id == BookModel.id)
        .where(
            BookmarkModel.user_id == user_id,
            BookmarkModel.deleted_at.is_(None),
            ChapterModel.deleted_at.is_(None),
            BookModel.deleted_at.is_(None),
        )
    )
    if book_id is not None:
        existing = session.execute(
            select(BookModel.id).where(
                BookModel.id == book_id,
                BookModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing is None:
            raise NotFoundError(
                "BOOK_NOT_FOUND",
                f"Book {book_id} does not exist",
            )
        bookmarks = bookmarks.where(BookModel.id == book_id)

    rows = session.execute(bookmarks.order_by(BookmarkModel.created_at.desc())).all()
    return [
        {
            "id": bookmark.id,
            "book_id": book.id,
            "book_title": book.title,
            "chapter_number": chapter.number,
            "chapter_title": chapter.title,
            "created_at": bookmark.created_at,
        }
        for bookmark, chapter, book in rows
    ]
    
def delete_bookmark(session: Session, user_id: int, bookmark_id: int) -> None:
    """Delete a bookmark of an user."""
    bookmark = session.execute(
        select(BookmarkModel).where(
            BookmarkModel.id == bookmark_id,
            BookmarkModel.user_id == user_id,
            BookmarkModel.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if bookmark is None:
        raise NotFoundError(
            "BOOKMARK_NOT_FOUND",
            f"Bookmark {bookmark_id} does not exist",
        )
    bookmark.deleted_at = datetime.now(timezone.utc)
    session.commit()