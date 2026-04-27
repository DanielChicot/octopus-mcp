import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.rest import OctopusRestClient

FIXTURES = Path(__file__).parent / "fixtures"


def _resp(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def _client(handler: httpx.MockTransport | None = None) -> OctopusRestClient:
    if handler is None:
        raise ValueError("handler required")
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://api.octopus.energy")
    return OctopusRestClient(
        OctopusCredentials(api_key="k", account_number="A-1"), http_client=http
    )


async def test_get_account_returns_typed_account() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/accounts/A-1/"
        return httpx.Response(200, json=_resp("account_sample.json"))

    async with _client(handler) as c:
        account = await c.get_account()
    assert account.number == "A-12345678"


async def test_get_consumption_passes_period_params_and_pages() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=_resp("consumption_sample.json"))

    async with _client(handler) as c:
        rows = await c.get_electricity_consumption(
            mpan="1234567890123",
            serial="ELEC001",
            period_from=datetime(2026, 4, 25, tzinfo=UTC),
            period_to=datetime(2026, 4, 26, tzinfo=UTC),
        )
    assert len(rows) == 2
    params = captured["params"]
    assert isinstance(params, dict)
    assert params["period_from"] == "2026-04-25T00:00:00+00:00"
    assert params["page_size"] == "25000"


async def test_get_consumption_follows_next_pages() -> None:
    pages = [
        {
            "count": 4,
            "next": "https://api.octopus.energy/v1/electricity-meter-points/1/meters/S/consumption/?page=2",
            "previous": None,
            "results": [
                {
                    "consumption": 0.1,
                    "interval_start": "2026-04-25T00:00:00Z",
                    "interval_end": "2026-04-25T00:30:00Z",
                },
                {
                    "consumption": 0.2,
                    "interval_start": "2026-04-25T00:30:00Z",
                    "interval_end": "2026-04-25T01:00:00Z",
                },
            ],
        },
        {
            "count": 4,
            "next": None,
            "previous": None,
            "results": [
                {
                    "consumption": 0.3,
                    "interval_start": "2026-04-25T01:00:00Z",
                    "interval_end": "2026-04-25T01:30:00Z",
                },
                {
                    "consumption": 0.4,
                    "interval_start": "2026-04-25T01:30:00Z",
                    "interval_end": "2026-04-25T02:00:00Z",
                },
            ],
        },
    ]
    seen: dict[str, int] = {"i": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        body = pages[seen["i"]]
        seen["i"] += 1
        return httpx.Response(200, json=body)

    async with _client(handler) as c:
        rows = await c.get_electricity_consumption(mpan="1", serial="S")
    assert len(rows) == 4
    assert seen["i"] == 2


async def test_list_products_unauthenticated_path() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=_resp("products_sample.json"))

    async with _client(handler) as c:
        products = await c.list_products()
    assert captured["path"] == "/v1/products/"
    assert products[0].code == "VAR-22-11-01"


async def test_get_unit_rates() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_resp("unit_rates_sample.json"))

    async with _client(handler) as c:
        rates = await c.get_electricity_unit_rates(
            product_code="VAR-22-11-01",
            tariff_code="E-1R-VAR-22-11-01-A",
        )
    assert len(rates) == 2
    assert rates[0].value_inc_vat == 26.25
