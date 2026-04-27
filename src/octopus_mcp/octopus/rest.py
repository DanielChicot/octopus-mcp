"""Async HTTP client for the Octopus public REST API."""

from __future__ import annotations

import base64
import logging
from datetime import datetime
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
from octopus_mcp.octopus.models import (
    Account,
    ConsumptionPage,
    ConsumptionRow,
    Product,
    ProductPage,
    StandingCharge,
    StandingChargePage,
    UnitRate,
    UnitRatePage,
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

    # ---- account ----

    async def get_account(self, account_number: str | None = None) -> Account:
        number = account_number or self._creds.account_number
        data = await self._get_json(f"/v1/accounts/{number}/")
        return Account.model_validate(data)

    # ---- consumption ----

    async def get_electricity_consumption(
        self,
        mpan: str,
        serial: str,
        *,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[ConsumptionRow]:
        return await self._consumption(
            f"/v1/electricity-meter-points/{mpan}/meters/{serial}/consumption/",
            period_from,
            period_to,
        )

    async def get_gas_consumption(
        self,
        mprn: str,
        serial: str,
        *,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[ConsumptionRow]:
        return await self._consumption(
            f"/v1/gas-meter-points/{mprn}/meters/{serial}/consumption/",
            period_from,
            period_to,
        )

    async def _consumption(
        self,
        path: str,
        period_from: datetime | None,
        period_to: datetime | None,
    ) -> list[ConsumptionRow]:
        params: dict[str, Any] = {"page_size": 25000, "order_by": "period"}
        if period_from is not None:
            params["period_from"] = period_from.isoformat()
        if period_to is not None:
            params["period_to"] = period_to.isoformat()

        rows: list[ConsumptionRow] = []
        next_url: str | None = path
        next_params: dict[str, Any] | None = params
        while next_url is not None:
            data = await self._get_json(next_url, params=next_params)
            page = ConsumptionPage.model_validate(data)
            rows.extend(page.results)
            next_url = self._strip_base(page.next)
            next_params = None  # next URL already includes params
        return rows

    @staticmethod
    def _strip_base(url: str | None) -> str | None:
        if url is None:
            return None
        if url.startswith(_BASE_URL):
            return url[len(_BASE_URL) :]
        return url

    # ---- products ----

    async def list_products(self) -> list[Product]:
        data = await self._get_json("/v1/products/")
        return ProductPage.model_validate(data).results

    async def get_product(self, code: str) -> dict[str, Any]:
        """Fetch full product detail.

        Returns the raw API response as a dict because the product-detail payload
        is large and varied (per-region tariff codes, sample quotes, etc.) and
        a typed model is deferred to v0.2. Callers should treat fields as
        optional and handle missing keys.
        """
        return await self._get_json(f"/v1/products/{code}/")

    # ---- tariff rates ----

    async def get_electricity_unit_rates(
        self, product_code: str, tariff_code: str
    ) -> list[UnitRate]:
        path = f"/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
        data = await self._get_json(path, params={"page_size": 1500})
        page = UnitRatePage.model_validate(data)
        if page.next is not None:
            _log.warning(
                "tariff rates page truncated at 1500 rows for %s/%s; pagination not yet implemented (v0.2)",
                product_code,
                tariff_code,
            )
        return page.results

    async def get_electricity_standing_charges(
        self, product_code: str, tariff_code: str
    ) -> list[StandingCharge]:
        path = f"/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standing-charges/"
        data = await self._get_json(path, params={"page_size": 1500})
        page = StandingChargePage.model_validate(data)
        if page.next is not None:
            _log.warning(
                "tariff rates page truncated at 1500 rows for %s/%s; pagination not yet implemented (v0.2)",
                product_code,
                tariff_code,
            )
        return page.results

    async def get_gas_unit_rates(self, product_code: str, tariff_code: str) -> list[UnitRate]:
        path = f"/v1/products/{product_code}/gas-tariffs/{tariff_code}/standard-unit-rates/"
        data = await self._get_json(path, params={"page_size": 1500})
        page = UnitRatePage.model_validate(data)
        if page.next is not None:
            _log.warning(
                "tariff rates page truncated at 1500 rows for %s/%s; pagination not yet implemented (v0.2)",
                product_code,
                tariff_code,
            )
        return page.results

    async def get_gas_standing_charges(
        self, product_code: str, tariff_code: str
    ) -> list[StandingCharge]:
        path = f"/v1/products/{product_code}/gas-tariffs/{tariff_code}/standing-charges/"
        data = await self._get_json(path, params={"page_size": 1500})
        page = StandingChargePage.model_validate(data)
        if page.next is not None:
            _log.warning(
                "tariff rates page truncated at 1500 rows for %s/%s; pagination not yet implemented (v0.2)",
                product_code,
                tariff_code,
            )
        return page.results
