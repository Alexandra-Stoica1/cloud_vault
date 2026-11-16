class ServiceError(Exception):
    """Base class for every business error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConflictError(ServiceError):
    """The resource already exists (HTTP 409)."""


class AuthenticationError(ServiceError):
    """Wrong credentials or an invalid / expired / revoked token (HTTP 401)."""
