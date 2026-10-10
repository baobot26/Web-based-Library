from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Iterator[Session]:
    """Assign database session to request, closes when request ends."""
    with SessionLocal() as session:
        yield session