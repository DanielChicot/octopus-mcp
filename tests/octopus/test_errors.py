import pytest
from octopus_mcp.octopus.errors import (
    AuthenticationError,
    AuthorizationError,
    CacheError,
    ConfigError,
    DataError,
    NotFoundError,
    OctopusError,
    RateLimitError,
    ServiceError,
)


def test_all_errors_inherit_from_octopus_error() -> None:
    for cls in (
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        NotFoundError,
        ServiceError,
        DataError,
        CacheError,
        ConfigError,
    ):
        assert issubclass(cls, OctopusError)


def test_rate_limit_error_carries_retry_after() -> None:
    err = RateLimitError("rate limited", retry_after_seconds=30)
    assert err.retry_after_seconds == 30


def test_not_found_error_carries_resource_hint() -> None:
    err = NotFoundError("missing", resource="meter:1234")
    assert err.resource == "meter:1234"


def test_data_error_carries_truncated_excerpt() -> None:
    err = DataError("bad shape", raw_excerpt="x" * 5000)
    assert len(err.raw_excerpt) <= 1024


def test_octopus_error_can_be_raised_and_caught() -> None:
    with pytest.raises(OctopusError):
        raise AuthenticationError("nope")
