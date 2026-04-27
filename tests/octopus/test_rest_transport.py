from collections.abc import Callable
from typing import Any

import httpx
import pytest
from tenacity import wait_fixed

import octopus_mcp.octopus.rest as rest_module
from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceError,
)
from octopus_mcp.octopus.rest import OctopusRestClient


def _creds() -> OctopusCredentials:
    return OctopusCredentials(api_key="sk_test", account_number="A-1")


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> OctopusRestClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://api.octopus.energy")
    return OctopusRestClient(_creds(), http_client=http)


async def test_get_uses_basic_auth() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"ok": True})

    async with _make_client(handler) as client:
        await client._get_json("/v1/products/")
    assert captured["auth"].startswith("Basic ")


async def test_401_raises_authentication_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid token"})

    async with _make_client(handler) as client:
        with pytest.raises(AuthenticationError):
            await client._get_json("/v1/products/")


async def test_403_raises_authorization_error() -> None:
    async with _make_client(lambda _: httpx.Response(403)) as client:
        with pytest.raises(AuthorizationError):
            await client._get_json("/v1/x")


async def test_404_raises_not_found_error() -> None:
    async with _make_client(lambda _: httpx.Response(404)) as client:
        with pytest.raises(NotFoundError):
            await client._get_json("/v1/x")


async def test_429_raises_rate_limit_with_retry_after() -> None:
    async with _make_client(lambda _: httpx.Response(429, headers={"Retry-After": "12"})) as client:
        with pytest.raises(RateLimitError) as exc:
            await client._get_json("/v1/x")
        assert exc.value.retry_after_seconds == 12


async def test_500_retries_then_raises_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    monkeypatch.setattr(rest_module, "_RETRY_WAIT", wait_fixed(0))

    async with _make_client(handler) as client:
        with pytest.raises(ServiceError):
            await client._get_json("/v1/x")
    assert calls["n"] == 3  # initial + 2 retries


async def test_500_then_200_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(rest_module, "_RETRY_WAIT", wait_fixed(0))

    async with _make_client(handler) as client:
        out = await client._get_json("/v1/x")
    assert out == {"ok": True}


async def test_transport_error_retries_then_raises_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rest_module, "_RETRY_WAIT", wait_fixed(0))
    calls: dict[str, int] = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("connection refused")

    async with _make_client(handler) as client:
        with pytest.raises(ServiceError):
            await client._get_json("/v1/x")
    assert calls["n"] == 3
