"""Domain errors and helpers that keep the API error format consistent.

All API errors are returned as ``{"error": "<human readable message>"}``,
matching the contract used by the frontend.
"""

from __future__ import annotations


class DomainError(Exception):
    """An expected, user-facing error (invalid query, upstream failure...)."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class UpstreamError(DomainError):
    """A third-party service (NASA POWER, Nominatim, OSM) failed or timed out."""


def error_message(error: Exception, fallback: str) -> str:
    """Return a safe message for an exception, hiding unexpected internals."""
    if isinstance(error, DomainError):
        return error.message
    return fallback
