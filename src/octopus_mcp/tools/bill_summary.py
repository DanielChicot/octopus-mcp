"""bill_summary thick tool."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from octopus_mcp.analysis.billing import ConsumptionPoint, compute_period_cost
from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow
from octopus_mcp.tools.period import PeriodSpec, resolve_period


def _windows(rows: Any) -> list[RateWindow]:
    return [
        RateWindow(valid_from=r.valid_from, valid_to=r.valid_to, value_inc_vat=r.value_inc_vat)
        for r in rows
    ]


async def bill_summary(
    *, period: PeriodSpec, ctx: Any, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    period_from, period_to = resolve_period(period, now=now)

    fuels_unavailable: list[str] = []
    fuel_outputs: list[dict[str, Any]] = []
    total_pence = 0

    for fuel in ("electricity", "gas"):
        meters = ctx.meters_repo.list_meters_for_account(ctx.creds.account_number, fuel=fuel)
        if not meters:
            fuels_unavailable.append(fuel)
            continue
        meter = meters[0]
        assignment = ctx.meters_repo.current_tariff_assignment(
            account_number=ctx.creds.account_number, fuel=fuel, at=period_from
        )
        if assignment is None:
            fuels_unavailable.append(fuel)
            continue

        await ctx.ensure_rates(
            product_code=assignment.product_code,
            tariff_code=assignment.tariff_code,
            fuel=fuel,
        )

        unit_rate_rows = ctx.rates_repo.get_unit_rates(assignment.tariff_code)
        sc_rate_rows = ctx.rates_repo.get_standing_charges(assignment.tariff_code)

        consumption_rows = await ctx.consumption_syncer.ensure(
            fuel=fuel,
            mpan_or_mprn=meter.mpan_or_mprn,
            serial_number=meter.serial_number,
            period_from=period_from,
            period_to=period_to,
            now=now,
        )
        consumption = [
            ConsumptionPoint(interval_start=r.interval_start, consumption_kwh=r.consumption_kwh)
            for r in consumption_rows
        ]
        cost = compute_period_cost(
            consumption=consumption,
            unit_rates=RateStream(_windows(unit_rate_rows)),
            standing_charges=RateStream(_windows(sc_rate_rows)),
            period_from=period_from,
            period_to=period_to,
        )
        total_kwh = sum(
            c.consumption_kwh for c in consumption if period_from <= c.interval_start < period_to
        )
        total_pence += cost.total_pence
        fuel_outputs.append(
            {
                "fuel": fuel,
                "tariff_code": assignment.tariff_code,
                "kwh": round(total_kwh, 4),
                "unit_pence": cost.unit_pence,
                "standing_pence": cost.standing_pence,
                "total_pence": cost.total_pence,
                "caveats": cost.caveats,
            }
        )

    return {
        "period": {"from": period_from.date().isoformat(), "to": period_to.date().isoformat()},
        "fuels": fuel_outputs,
        "fuels_unavailable": fuels_unavailable,
        "totals": {"total_pence": total_pence, "pounds": f"£{total_pence / 100:.2f}"},
    }
