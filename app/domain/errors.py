class DomainError(Exception):
    """A business rule was broken."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(DomainError):
    """The resource does not exist or was deleted."""


class ForbiddenError(DomainError):
    """Entering forbidden territory."""


class ConflictError(DomainError):
    """The request would create a conflict, should be a duplicate."""


class AuthenticationError(DomainError):
    """Wrong identity: bad email or password."""


