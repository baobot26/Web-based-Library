from app.domain.entities import User
from app.domain.errors import AuthenticationError, ConflictError
from app.domain.repositories import UserRepository
from app.services.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def register(self, email: str, password: str, name: str) -> User:
        email = email.lower()
        if self.users.get_by_email(email) is not None:
            raise ConflictError("EMAIL_TAKEN", f"Email {email} is already registered")
        return self.users.add(email, name, hash_password(password))

    def login(self, email: str, password: str) -> str:
        user = self.users.get_by_email(email.lower())
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("INVALID_CREDENTIALS", "Wrong email or password")
        return create_access_token(user.id)
