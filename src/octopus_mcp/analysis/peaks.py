"""Peak-half-hour detection."""

from __future__ import annotations

from collections.abc import Iterable

from octopus_mcp.analysis.billing import ConsumptionPoint


def top_n_half_hours(rows: Iterable[ConsumptionPoint], *, n: int) -> list[ConsumptionPoint]:
    return sorted(rows, key=lambda r: r.consumption_kwh, reverse=True)[:n]
