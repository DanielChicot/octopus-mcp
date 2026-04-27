"""Shared per-server context handed to each tool."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC
from typing import Any

from octopus_mcp.cache.consumption import ConsumptionRepo
from octopus_mcp.cache.meters import MetersRepo
from octopus_mcp.cache.products import ProductsRepo
from octopus_mcp.cache.rates import RatesRepo
from octopus_mcp.cache.sync import ConsumptionSyncer
from octopus_mcp.cache.sync_state import SyncStateRepo
from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.rest import OctopusRestClient


@dataclass
class ToolContext:
    creds: OctopusCredentials
    rest: OctopusRestClient
    conn: sqlite3.Connection
    consumption_repo: ConsumptionRepo
    rates_repo: RatesRepo
    meters_repo: MetersRepo
    products_repo: ProductsRepo
    sync_state: SyncStateRepo
    consumption_syncer: ConsumptionSyncer


@dataclass
class _Helpers:
    ensure_rates: Callable[..., Coroutine[Any, Any, None]]
    resolve_target_tariff_code: Callable[..., Coroutine[Any, Any, str]]


def build_helpers(ctx: ToolContext) -> _Helpers:
    """Attach `ensure_rates` and `resolve_target_tariff_code` async closures to the context."""
    from datetime import datetime

    from octopus_mcp.cache.rates import RateRow
    from octopus_mcp.octopus.errors import NotFoundError

    async def ensure_rates(*, product_code: str, tariff_code: str, fuel: str) -> None:
        key = f"rates:{fuel}:{tariff_code}"
        now = datetime.now(UTC)
        if ctx.sync_state.is_fresh(key, now=now):
            return
        if fuel == "electricity":
            unit_rows = await ctx.rest.get_electricity_unit_rates(product_code, tariff_code)
            sc_rows = await ctx.rest.get_electricity_standing_charges(product_code, tariff_code)
        else:
            unit_rows = await ctx.rest.get_gas_unit_rates(product_code, tariff_code)
            sc_rows = await ctx.rest.get_gas_standing_charges(product_code, tariff_code)
        ctx.rates_repo.upsert_unit_rates(
            tariff_code=tariff_code,
            fuel=fuel,
            rows=[
                RateRow(
                    valid_from=r.valid_from,
                    valid_to=r.valid_to,
                    value_inc_vat=r.value_inc_vat,
                    value_exc_vat=r.value_exc_vat,
                )
                for r in unit_rows
            ],
        )
        ctx.rates_repo.upsert_standing_charges(
            tariff_code=tariff_code,
            fuel=fuel,
            rows=[
                RateRow(
                    valid_from=r.valid_from,
                    valid_to=r.valid_to,
                    value_inc_vat=r.value_inc_vat,
                    value_exc_vat=r.value_exc_vat,
                )
                for r in sc_rows
            ],
        )
        ctx.sync_state.touch(key, at=now, ttl_seconds=86400)

    async def resolve_target_tariff_code(product_code: str, fuel: str) -> str:
        product = await ctx.rest.get_product(product_code)
        section_key = (
            "single_register_electricity_tariffs"
            if fuel == "electricity"
            else "single_register_gas_tariffs"
        )
        section = product.get(section_key, {})
        if not section:
            raise NotFoundError(
                f"Product {product_code} has no {fuel} tariffs",
                resource=product_code,
            )
        first_region = next(iter(section.values()))
        if "direct_debit_monthly" in first_region:
            return first_region["direct_debit_monthly"]["code"]  # type: ignore[no-any-return]
        if "direct_debit_quarterly" in first_region:
            return first_region["direct_debit_quarterly"]["code"]  # type: ignore[no-any-return]
        for variant in first_region.values():
            if "code" in variant:
                return variant["code"]  # type: ignore[no-any-return]
        raise NotFoundError(
            f"No tariff code found in product {product_code}", resource=product_code
        )

    ctx.ensure_rates = ensure_rates  # type: ignore[attr-defined]
    ctx.resolve_target_tariff_code = resolve_target_tariff_code  # type: ignore[attr-defined]
    return _Helpers(
        ensure_rates=ensure_rates, resolve_target_tariff_code=resolve_target_tariff_code
    )
