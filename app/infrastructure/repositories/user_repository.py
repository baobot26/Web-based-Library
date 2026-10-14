from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.domain.errors import ConflictError
from app.infrastructure.models import UserModel


class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        row = self.session.scalar(select(UserModel).where(UserModel.email == email))
        return _to_entity(row) if row else None

    def add(self, email: str, name: str, password_hash: str) -> User:
        row = UserModel(email=email, name=name, password_hash=password_hash)
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ConflictError("EMAIL_TAKEN", f"Email {email} is already registered") from None
        self.session.refresh(row)
        return _to_entity(row)


def _to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        name=row.name,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )
