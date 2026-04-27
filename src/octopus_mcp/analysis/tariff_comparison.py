"""Tariff comparison: replay actual usage against another tariff."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from octopus_mcp.analysis.billing import ConsumptionPoint, compute_period_cost
from octopus_mcp.analysis.rate_lookup import RateStream

_DEFAULT_CAVEATS = [
    "Models a pure tariff swap; does not include Saving Sessions, Octoplus, or referral credits.",
    "Assumes your usage pattern is unchanged on the target tariff. Time-of-use tariffs typically reward behaviour change — actual savings often higher.",
]


@dataclass(frozen=True)
class FuelInputs:
    fuel: Literal["electricity", "gas"]
    consumption: list[ConsumptionPoint]
    current_unit_rates: RateStream
    current_standing: RateStream
    target_unit_rates: RateStream
    target_standing: RateStream


@dataclass(frozen=True)
class FuelComparison:
    fuel: str
    current_unit_pence: int
    current_standing_pence: int
    current_total_pence: int
    target_unit_pence: int
    target_standing_pence: int
    target_total_pence: int
    delta_pence: int


@dataclass(frozen=True)
class DayBreakdown:
    date: date
    current_pence: int
    target_pence: int
    delta_pence: int


@dataclass(frozen=True)
class TariffComparison:
    period: tuple[date, date]
    target_product_code: str
    fuels: list[FuelComparison]
    total_current_pence: int
    total_target_pence: int
    total_delta_pence: int
    pounds_summary: str
    breakdown_by_day: list[DayBreakdown]
    caveats: list[str] = field(default_factory=list)


def _format_pounds(delta_pence: int) -> str:
    abs_pounds = abs(delta_pence) / 100.0
    if delta_pence < 0:
        return f"Saves £{abs_pounds:.2f}"
    if delta_pence > 0:
        return f"Costs £{abs_pounds:.2f} more"
    return "Same cost"


def compare_tariffs(
    *,
    target_product_code: str,
    period_from: datetime,
    period_to: datetime,
    fuels: list[FuelInputs],
) -> TariffComparison:
    fuel_results: list[FuelComparison] = []
    day_buckets: dict[date, tuple[int, int]] = {}

    for f in fuels:
        cur = compute_period_cost(
            consumption=f.consumption,
            unit_rates=f.current_unit_rates,
            standing_charges=f.current_standing,
            period_from=period_from,
            period_to=period_to,
        )
        tgt = compute_period_cost(
            consumption=f.consumption,
            unit_rates=f.target_unit_rates,
            standing_charges=f.target_standing,
            period_from=period_from,
            period_to=period_to,
        )
        fuel_results.append(
            FuelComparison(
                fuel=f.fuel,
                current_unit_pence=cur.unit_pence,
                current_standing_pence=cur.standing_pence,
                current_total_pence=cur.total_pence,
                target_unit_pence=tgt.unit_pence,
                target_standing_pence=tgt.standing_pence,
                target_total_pence=tgt.total_pence,
                delta_pence=tgt.total_pence - cur.total_pence,
            )
        )

        d = period_from.date()
        end_d = period_to.date()
        while d < end_d:
            day_start = datetime(d.year, d.month, d.day, tzinfo=UTC)
            day_end = day_start + timedelta(days=1)
            cur_d = compute_period_cost(
                consumption=f.consumption,
                unit_rates=f.current_unit_rates,
                standing_charges=f.current_standing,
                period_from=day_start,
                period_to=day_end,
            )
            tgt_d = compute_period_cost(
                consumption=f.consumption,
                unit_rates=f.target_unit_rates,
                standing_charges=f.target_standing,
                period_from=day_start,
                period_to=day_end,
            )
            cur_p, tgt_p = day_buckets.get(d, (0, 0))
            day_buckets[d] = (cur_p + cur_d.total_pence, tgt_p + tgt_d.total_pence)
            d += timedelta(days=1)

    breakdown = [
        DayBreakdown(date=d, current_pence=c, target_pence=t, delta_pence=t - c)
        for d, (c, t) in sorted(day_buckets.items())
    ]

    total_current = sum(f.current_total_pence for f in fuel_results)
    total_target = sum(f.target_total_pence for f in fuel_results)
    total_delta = total_target - total_current

    return TariffComparison(
        period=(period_from.date(), period_to.date()),
        target_product_code=target_product_code,
        fuels=fuel_results,
        total_current_pence=total_current,
        total_target_pence=total_target,
        total_delta_pence=total_delta,
        pounds_summary=_format_pounds(total_delta),
        breakdown_by_day=breakdown,
        caveats=list(_DEFAULT_CAVEATS),
    )
