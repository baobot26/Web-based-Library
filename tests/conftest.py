import itertools
import os
from datetime import datetime, timezone

TEST_DATABASE_URL = "postgresql+psycopg://hello:world@localhost:5432/library_test"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.infrastructure.db import get_session  # noqa: E402
from app.infrastructure.models import Base, BookModel, ChapterModel, UserModel  # noqa: E402
from app.main import app  # noqa: E402

_seq = itertools.count(1)


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """A fresh session with every table emptied."""
    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make(name="An", email=None):
        n = next(_seq)
        user = UserModel(
            email=email or f"user{n}@example.com",
            password_hash="hashed",
            name=name,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def make_book(db_session):
    def _make(uploader, title="A Book", description="Some description", created_at=None, deleted_at=None):
        book = BookModel(
            title=title,
            description=description,
            uploader_id=uploader.id,
            created_at=created_at,
            deleted_at=deleted_at,
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return _make


@pytest.fixture()
def make_chapter(db_session):
    def _make(book, number, title="Chapter", content="Once upon a time...", created_at=None, deleted_at=None):
        chapter = ChapterModel(
            book_id=book.id,
            number=number,
            title=title,
            content=content,
            created_at=created_at,
            deleted_at=deleted_at,
        )
        db_session.add(chapter)
        db_session.commit()
        db_session.refresh(chapter)
        return chapter

    return _make
