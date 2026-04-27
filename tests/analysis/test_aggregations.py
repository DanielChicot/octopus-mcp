from datetime import datetime

from octopus_mcp.analysis.aggregations import GroupBy, aggregate, summary_stats
from octopus_mcp.analysis.billing import ConsumptionPoint


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_aggregate_by_day_sums_per_local_day() -> None:
    rows = [
        _c("2026-04-25T00:00:00Z", 1.0),
        _c("2026-04-25T12:00:00Z", 2.0),
        _c("2026-04-26T00:00:00Z", 4.0),
    ]
    out = aggregate(rows, group_by=GroupBy.DAY, tz="Europe/London")
    assert len(out) == 2
    assert out[0].label == "2026-04-25"
    assert out[0].kwh == 3.0
    assert out[1].kwh == 4.0


def test_aggregate_by_hour_buckets_half_hours() -> None:
    rows = [
        _c("2026-04-25T08:00:00Z", 0.5),
        _c("2026-04-25T08:30:00Z", 0.7),
        _c("2026-04-25T09:00:00Z", 0.4),
    ]
    out = aggregate(rows, group_by=GroupBy.HOUR, tz="Europe/London")
    labels = [b.label for b in out]
    # In April London is BST (UTC+1)
    assert labels[0] == "2026-04-25 09:00"
    assert out[0].kwh == 1.2


def test_summary_stats_min_max_mean_stdev() -> None:
    s = summary_stats([1.0, 2.0, 3.0, 4.0])
    assert s.min == 1.0
    assert s.max == 4.0
    assert s.mean == 2.5
    assert round(s.stdev, 4) == 1.2910


def test_summary_stats_empty_returns_zeros() -> None:
    s = summary_stats([])
    assert s.min == s.max == s.mean == s.stdev == 0.0
