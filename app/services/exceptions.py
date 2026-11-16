class ServiceError(Exception):
    """Base class for every business error (HTTP 400 unless a subclass says otherwise)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BusinessRuleError(ServiceError):
    """The request breaks a business rule, e.g. a tier limit (HTTP 400)."""


class AuthenticationError(ServiceError):
    """Wrong credentials or an invalid / expired / revoked token (HTTP 401)."""


class PermissionDeniedError(ServiceError):
    """The user is authenticated but not allowed to do this (HTTP 403)."""


class NotFoundError(ServiceError):
    """The resource does not exist or is not visible to the user (HTTP 404)."""


class ConflictError(ServiceError):
    """The resource already exists (HTTP 409)."""
