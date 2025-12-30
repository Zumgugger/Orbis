"""
Application-wide exception classes
Provides consistent error handling across the application
"""
from __future__ import annotations

from typing import Any


class OrbisError(Exception):
    """Base exception for all Orbis application errors"""

    def __init__(
        self,
        message: str = "An error occurred",
        error_code: str = "error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to JSON-serializable dict"""
        result: dict[str, Any] = {
            "error": self.error_code,
            "message": self.message,
            "status": self.status_code,
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(OrbisError):
    """Raised when input validation fails"""

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=400,
            details=error_details,
        )
        self.field = field


class NotFoundError(OrbisError):
    """Raised when a requested resource is not found"""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id is not None:
            details["resource_id"] = resource_id
        super().__init__(
            message=message,
            error_code="not_found",
            status_code=404,
            details=details if details else None,
        )


class ForbiddenError(OrbisError):
    """Raised when user lacks permission for an action"""

    def __init__(
        self,
        message: str = "Access denied",
        required_permission: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(
            message=message,
            error_code="forbidden",
            status_code=403,
            details=details if details else None,
        )


class UnauthorizedError(OrbisError):
    """Raised when authentication is required but missing or invalid"""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            error_code="unauthorized",
            status_code=401,
        )


class ConflictError(OrbisError):
    """Raised when there's a conflict with current state (e.g., duplicate)"""

    def __init__(
        self,
        message: str = "Resource conflict",
        conflict_type: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if conflict_type:
            details["conflict_type"] = conflict_type
        super().__init__(
            message=message,
            error_code="conflict",
            status_code=409,
            details=details if details else None,
        )


class RateLimitError(OrbisError):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            error_code="rate_limit_exceeded",
            status_code=429,
            details=details if details else None,
        )


class ServiceError(OrbisError):
    """Raised when an external service fails"""

    def __init__(
        self,
        message: str = "Service unavailable",
        service_name: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if service_name:
            details["service"] = service_name
        super().__init__(
            message=message,
            error_code="service_error",
            status_code=503,
            details=details if details else None,
        )


# Re-export ValidationError from validation.py for backward compatibility
# This allows: from exceptions import ValidationError
# while validation.py keeps its own ValidationError for form validation
