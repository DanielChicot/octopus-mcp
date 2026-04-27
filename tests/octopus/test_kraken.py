from collections.abc import Callable

import httpx
import pytest
from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import AuthenticationError
from octopus_mcp.octopus.kraken import KrakenClient

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> KrakenClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://api.octopus.energy")
    return KrakenClient(
        OctopusCredentials(api_key="sk_test", account_number="A-1"),
        http_client=http,
    )


async def test_first_call_mints_jwt_and_uses_it() -> None:
    calls = {"mints": 0, "queries": 0}
    last_auth: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "obtainKrakenToken" in body:
            calls["mints"] += 1
            return httpx.Response(200, json={"data": {"obtainKrakenToken": {"token": "JWT-FAKE"}}})
        calls["queries"] += 1
        last_auth["v"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": {"viewer": {"id": "vid"}}})

    async with _client(handler) as kc:
        out = await kc.query("query { viewer { id } }")
    assert calls["mints"] == 1
    assert calls["queries"] == 1
    assert out == {"viewer": {"id": "vid"}}
    assert last_auth["v"] == "JWT JWT-FAKE"


async def test_unauthenticated_response_triggers_one_remint_then_retry() -> None:
    state = {"phase": 0, "mints": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "obtainKrakenToken" in body:
            state["mints"] += 1
            return httpx.Response(
                200, json={"data": {"obtainKrakenToken": {"token": f"T{state['mints']}"}}}
            )
        state["phase"] += 1
        if state["phase"] == 1:
            return httpx.Response(
                200,
                json={
                    "errors": [
                        {"extensions": {"errorCode": "KT-CT-1124"}, "message": "unauthorised"}
                    ]
                },
            )
        return httpx.Response(200, json={"data": {"viewer": {"id": "ok"}}})

    async with _client(handler) as kc:
        out = await kc.query("query { viewer { id } }")
    assert out == {"viewer": {"id": "ok"}}
    assert state["mints"] == 2  # initial mint + remint after 1124


async def test_persistent_auth_failure_raises_authentication_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "obtainKrakenToken" in body:
            return httpx.Response(200, json={"data": {"obtainKrakenToken": {"token": "T"}}})
        return httpx.Response(
            200, json={"errors": [{"extensions": {"errorCode": "KT-CT-1124"}, "message": "no"}]}
        )

    async with _client(handler) as kc:
        with pytest.raises(AuthenticationError):
            await kc.query("query {}")
