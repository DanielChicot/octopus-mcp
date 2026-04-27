"""Time-bucket aggregations and summary statistics."""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from octopus_mcp.analysis.billing import ConsumptionPoint


class GroupBy(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class Bucket:
    label: str
    kwh: float


@dataclass(frozen=True)
class Stats:
    min: float
    max: float
    mean: float
    stdev: float


def _bucket_label(local: datetime, group_by: GroupBy) -> str:
    if group_by == GroupBy.HOUR:
        return local.strftime("%Y-%m-%d %H:00")
    if group_by == GroupBy.DAY:
        return local.strftime("%Y-%m-%d")
    if group_by == GroupBy.WEEK:
        iso_year, iso_week, _ = local.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if group_by == GroupBy.MONTH:
        return local.strftime("%Y-%m")
    raise ValueError(group_by)


def aggregate(
    rows: Iterable[ConsumptionPoint],
    *,
    group_by: GroupBy,
    tz: str = "Europe/London",
) -> list[Bucket]:
    zone = ZoneInfo(tz)
    buckets: dict[str, float] = defaultdict(float)
    for r in rows:
        local = r.interval_start.astimezone(zone)
        if group_by == GroupBy.HOUR:
            local = local.replace(minute=0, second=0, microsecond=0)
        elif group_by == GroupBy.DAY:
            local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        label = _bucket_label(local, group_by)
        buckets[label] += r.consumption_kwh
    return [Bucket(label=k, kwh=round(v, 4)) for k, v in sorted(buckets.items())]


def summary_stats(values: list[float]) -> Stats:
    if not values:
        return Stats(0.0, 0.0, 0.0, 0.0)
    return Stats(
        min=min(values),
        max=max(values),
        mean=statistics.mean(values),
        stdev=statistics.stdev(values) if len(values) > 1 else 0.0,
    )
