"""Custom exceptions for BuyerOS.

Provides domain-specific exceptions for better error handling and debugging.
"""

from typing import Any, Optional


class BuyerOSError(Exception):
    """Base exception for BuyerOS."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ServiceUnavailableError(BuyerOSError):
    """Raised when a required service is unavailable."""

    def __init__(self, service: str, details: Optional[dict] = None) -> None:
        super().__init__(f"Service unavailable: {service}", details)
        self.service = service


class AuthenticationError(BuyerOSError):
    """Raised when authentication fails."""

    def __init__(self, reason: str = "Authentication failed", details: Optional[dict] = None) -> None:
        super().__init__(reason, details)


class ValidationError(BuyerOSError):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str, details: Optional[dict] = None) -> None:
        super().__init__(f"Validation error on {field}: {message}", details)
        self.field = field


class DatabaseError(BuyerOSError):
    """Raised when a database operation fails."""

    def __init__(self, operation: str, details: Optional[dict] = None) -> None:
        super().__init__(f"Database error during {operation}", details)
        self.operation = operation


class ExternalAPIError(BuyerOSError):
    """Raised when an external API call fails."""

    def __init__(self, api: str, status_code: Optional[int] = None, details: Optional[dict] = None) -> None:
        super().__init__(f"External API error: {api}", details)
        self.api = api
        self.status_code = status_code


class TaskError(BuyerOSError):
    """Raised when a task operation fails."""

    def __init__(self, task_id: str, message: str, details: Optional[dict] = None) -> None:
        super().__init__(f"Task error {task_id}: {message}", details)
        self.task_id = task_id
