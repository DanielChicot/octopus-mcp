"""Thin pass-through tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any


async def get_account(*, rest: Any) -> dict[str, Any]:
    account = await rest.get_account()
    return account.model_dump(mode="json")  # type: ignore[no-any-return]


async def list_products(*, rest: Any) -> list[dict[str, Any]]:
    products = await rest.list_products()
    return [p.model_dump(mode="json") for p in products]


async def get_product(code: str, *, rest: Any) -> dict[str, Any]:
    return await rest.get_product(code)  # type: ignore[no-any-return]


async def get_consumption_raw(
    fuel: str,
    mpan_or_mprn: str,
    serial_number: str,
    period_from: datetime,
    period_to: datetime,
    *,
    rest: Any,
) -> list[dict[str, Any]]:
    if fuel == "electricity":
        rows = await rest.get_electricity_consumption(
            mpan=mpan_or_mprn, serial=serial_number, period_from=period_from, period_to=period_to
        )
    else:
        rows = await rest.get_gas_consumption(
            mprn=mpan_or_mprn, serial=serial_number, period_from=period_from, period_to=period_to
        )
    return [
        {
            "interval_start": r.interval_start.isoformat(),
            "interval_end": r.interval_end.isoformat(),
            "consumption_kwh": r.consumption,
        }
        for r in rows
    ]
