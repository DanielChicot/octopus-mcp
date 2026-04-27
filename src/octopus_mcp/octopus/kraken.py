"""Kraken GraphQL client with JWT lifecycle.

The token is short-lived (~1h). We mint on first use and remint exactly once
on an unauthenticated response, then surface the error.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import AuthenticationError, DataError, ServiceError

_GRAPHQL_PATH = "/v1/graphql/"
_AUTH_ERROR_CODES = {"KT-CT-1124", "KT-CT-1139", "KT-CT-1112"}

_log = logging.getLogger(__name__)

_OBTAIN_TOKEN_MUTATION = """
mutation ObtainToken($apiKey: String!) {
  obtainKrakenToken(input: { APIKey: $apiKey }) {
    token
  }
}
"""


class KrakenClient:
    def __init__(
        self,
        credentials: OctopusCredentials,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._creds = credentials
        self._token: str | None = None
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url="https://api.octopus.energy", timeout=httpx.Timeout(30.0)
        )

    async def __aenter__(self) -> KrakenClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def _mint_token(self) -> str:
        resp = await self._http.post(
            _GRAPHQL_PATH,
            json={"query": _OBTAIN_TOKEN_MUTATION, "variables": {"apiKey": self._creds.api_key}},
        )
        if resp.status_code >= 500:
            raise ServiceError(f"Kraken auth upstream error {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as e:
            raise DataError("Kraken returned non-JSON during auth", raw_excerpt=resp.text) from e
        if "errors" in data:
            raise AuthenticationError(f"Kraken refused to mint token: {data['errors']}")
        token = data.get("data", {}).get("obtainKrakenToken", {}).get("token")
        if not token:
            raise DataError("Kraken auth response missing token", raw_excerpt=resp.text)
        return token  # type: ignore[no-any-return]

    async def query(self, document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._token is None:
            self._token = await self._mint_token()

        for attempt in range(2):
            resp = await self._http.post(
                _GRAPHQL_PATH,
                json={"query": document, "variables": variables or {}},
                headers={"Authorization": f"JWT {self._token}"},
            )
            if resp.status_code >= 500:
                raise ServiceError(f"Kraken upstream {resp.status_code}")
            try:
                payload = resp.json()
            except ValueError as e:
                raise DataError("Kraken returned non-JSON", raw_excerpt=resp.text) from e

            if "errors" in payload:
                codes = {(e.get("extensions") or {}).get("errorCode") for e in payload["errors"]}
                if codes & _AUTH_ERROR_CODES and attempt == 0:
                    self._token = await self._mint_token()
                    continue
                if codes & _AUTH_ERROR_CODES:
                    raise AuthenticationError(
                        f"Kraken auth failed after retry: {payload['errors']}"
                    )
                raise DataError(f"Kraken returned errors: {payload['errors']}")
            return payload.get("data", {})  # type: ignore[no-any-return]
        raise AuthenticationError("Kraken auth failed after retry")
