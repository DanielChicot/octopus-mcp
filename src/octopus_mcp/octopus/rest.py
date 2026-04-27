"""Async HTTP client for the Octopus public REST API."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceError,
)

_BASE_URL = "https://api.octopus.energy"
_log = logging.getLogger(__name__)

# Exposed at module level so tests can monkeypatch it to wait_fixed(0).
_RETRY_WAIT = wait_exponential(multiplier=0.5, min=0.5, max=8)


class _RetryableHTTPError(Exception):
    pass


class OctopusRestClient:
    """Thin wrapper around httpx with auth, retry, and error mapping."""

    def __init__(
        self,
        credentials: OctopusCredentials,
        *,
        http_client: httpx.AsyncClient | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._creds = credentials
        self._max_attempts = max_attempts
        token = base64.b64encode(f"{credentials.api_key}:".encode()).decode()
        self._auth_header = {"Authorization": f"Basic {token}"}
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(30.0),
        )

    async def __aenter__(self) -> OctopusRestClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        import octopus_mcp.octopus.rest as _self_module

        async def _attempt() -> dict[str, Any]:
            resp = await self._http.get(path, params=params, headers=self._auth_header)
            return self._handle(resp)

        try:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_attempt(self._max_attempts),
                wait=_self_module._RETRY_WAIT,
                retry=retry_if_exception_type((_RetryableHTTPError, httpx.TransportError)),
            ):
                with attempt:
                    return await _attempt()
        except (_RetryableHTTPError, httpx.TransportError) as e:
            raise ServiceError(str(e)) from e
        raise ServiceError(
            "unreachable"
        )  # pragma: no cover  # tenacity reraise=True keeps the loop above; this is defensive

    @staticmethod
    def _handle(resp: httpx.Response) -> dict[str, Any]:
        if 200 <= resp.status_code < 300:
            return resp.json()  # type: ignore[no-any-return]
        if resp.status_code == 401:
            raise AuthenticationError("Octopus API rejected credentials (401)")
        if resp.status_code == 403:
            raise AuthorizationError("Octopus API forbade request (403)")
        if resp.status_code == 404:
            raise NotFoundError(f"Resource not found: {resp.request.url.path}")
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Octopus API rate-limited",
                retry_after_seconds=int(ra) if ra and ra.isdigit() else None,
            )
        if 500 <= resp.status_code < 600:
            raise _RetryableHTTPError(f"upstream {resp.status_code}")
        raise ServiceError(f"Unexpected status {resp.status_code}")
