from datetime import datetime

from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.analysis.peaks import top_n_half_hours


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_returns_top_n_descending() -> None:
    rows = [
        _c("2026-04-25T00:00:00Z", 0.3),
        _c("2026-04-25T18:00:00Z", 2.5),
        _c("2026-04-25T19:00:00Z", 3.1),
        _c("2026-04-25T20:00:00Z", 1.8),
    ]
    peaks = top_n_half_hours(rows, n=2)
    assert len(peaks) == 2
    assert peaks[0].consumption_kwh == 3.1
    assert peaks[1].consumption_kwh == 2.5


def test_n_larger_than_input_returns_all_sorted() -> None:
    rows = [_c("2026-04-25T00:00:00Z", 0.1), _c("2026-04-25T01:00:00Z", 0.2)]
    peaks = top_n_half_hours(rows, n=10)
    assert len(peaks) == 2
    assert peaks[0].consumption_kwh == 0.2


def test_empty_input_returns_empty() -> None:
    assert top_n_half_hours([], n=5) == []
