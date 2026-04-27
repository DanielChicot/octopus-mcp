"""current_tariff thick tool."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


async def current_tariff(*, ctx: Any, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    await ctx.ensure_account_bootstrapped()
    out: list[dict[str, Any]] = []

    for fuel in ("electricity", "gas"):
        assignment = ctx.meters_repo.current_tariff_assignment(
            account_number=ctx.creds.account_number, fuel=fuel, at=now
        )
        if assignment is None:
            continue
        await ctx.ensure_rates(
            product_code=assignment.product_code,
            tariff_code=assignment.tariff_code,
            fuel=fuel,
        )
        unit_rates = ctx.rates_repo.get_unit_rates(assignment.tariff_code)
        sc_rates = ctx.rates_repo.get_standing_charges(assignment.tariff_code)
        latest_unit = max(unit_rates, key=lambda r: r.valid_from) if unit_rates else None
        latest_sc = max(sc_rates, key=lambda r: r.valid_from) if sc_rates else None
        out.append(
            {
                "fuel": fuel,
                "product_code": assignment.product_code,
                "tariff_code": assignment.tariff_code,
                "unit_rate_pence_inc_vat": latest_unit.value_inc_vat if latest_unit else None,
                "standing_charge_pence_inc_vat": latest_sc.value_inc_vat if latest_sc else None,
            }
        )

    return {"as_of": now.isoformat(), "fuels": out}
