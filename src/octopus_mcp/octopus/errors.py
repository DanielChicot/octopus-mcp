"""Exception hierarchy for the Octopus client."""

from __future__ import annotations


class OctopusError(Exception):
    """Base class for all Octopus client errors."""


class AuthenticationError(OctopusError):
    """401 from upstream, or missing/bad credentials."""


class AuthorizationError(OctopusError):
    """403 from upstream."""


class RateLimitError(OctopusError):
    """429 from upstream."""

    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class NotFoundError(OctopusError):
    """404 from upstream, or a missing resource we can name."""

    def __init__(self, message: str, *, resource: str | None = None) -> None:
        super().__init__(message)
        self.resource = resource


class ServiceError(OctopusError):
    """5xx from upstream."""


class DataError(OctopusError):
    """Unexpected response shape."""

    _MAX_EXCERPT = 1024

    def __init__(self, message: str, *, raw_excerpt: str | None = None) -> None:
        super().__init__(message)
        self.raw_excerpt = (raw_excerpt or "")[: self._MAX_EXCERPT]


class CacheError(OctopusError):
    """SQLite or repository failure."""


class ConfigError(OctopusError):
    """Missing or invalid configuration."""
