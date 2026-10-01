"""Domain error hierarchy.

Use cases raise these; the HTTP layer maps each class to a status code in one
place. ``code`` is a stable machine-readable identifier that clients may branch on.
"""

from collections.abc import Mapping
from typing import ClassVar


class DomainError(Exception):
    code: ClassVar[str] = "domain_error"

    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: Mapping[str, object] = details or {}


class NotFoundError(DomainError):
    """The resource does not exist, or belongs to a tenant the caller cannot see."""

    code = "not_found"


class PermissionDeniedError(DomainError):
    code = "permission_denied"


class UnauthenticatedError(DomainError):
    code = "unauthenticated"


class ValidationError(DomainError):
    code = "validation_failed"


class ConflictError(DomainError):
    code = "conflict"


class InsufficientCreditsError(DomainError):
    code = "insufficient_credits"


class RateLimitedError(DomainError):
    code = "rate_limited"


class ExternalServiceError(DomainError):
    """A dependency failed. ``transient`` tells the caller whether a retry can help."""

    code = "external_service_error"

    def __init__(
        self,
        message: str,
        *,
        transient: bool,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.transient = transient
