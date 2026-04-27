"""usage_breakdown thick tool."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from octopus_mcp.analysis.aggregations import GroupBy, aggregate, summary_stats
from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.tools.period import PeriodSpec, resolve_period

GroupByLiteral = Literal["hour", "day", "week", "month"]


async def usage_breakdown(
    *,
    period: PeriodSpec,
    group_by: GroupByLiteral = "day",
    ctx: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    period_from, period_to = resolve_period(period, now=now)
    gb = GroupBy(group_by)

    breakdowns: dict[str, list[dict[str, Any]]] = {}
    stats: dict[str, dict[str, float]] = {}

    for fuel in ("electricity", "gas"):
        meters = ctx.meters_repo.list_meters_for_account(ctx.creds.account_number, fuel=fuel)
        if not meters:
            continue
        meter = meters[0]
        rows = await ctx.consumption_syncer.ensure(
            fuel=fuel,
            mpan_or_mprn=meter.mpan_or_mprn,
            serial_number=meter.serial_number,
            period_from=period_from,
            period_to=period_to,
            now=now,
        )
        points = [
            ConsumptionPoint(interval_start=r.interval_start, consumption_kwh=r.consumption_kwh)
            for r in rows
        ]
        buckets = aggregate(points, group_by=gb)
        breakdowns[fuel] = [{"label": b.label, "kwh": b.kwh} for b in buckets]
        s = summary_stats([b.kwh for b in buckets])
        stats[fuel] = {"min": s.min, "max": s.max, "mean": s.mean, "stdev": s.stdev}

    return {
        "period": {"from": period_from.date().isoformat(), "to": period_to.date().isoformat()},
        "group_by": group_by,
        "fuel_breakdowns": breakdowns,
        "stats": stats,
    }
