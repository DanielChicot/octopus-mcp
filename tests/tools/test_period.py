from datetime import UTC, date, datetime

import pytest

from octopus_mcp.tools.period import PeriodSpec, resolve_period


def _now() -> datetime:
    return datetime(2026, 4, 26, 12, 0, tzinfo=UTC)


def test_last_month() -> None:
    pf, pt = resolve_period(PeriodSpec(kind="last_month"), now=_now())
    assert (pf.year, pf.month, pf.day) == (2026, 3, 1)
    assert (pt.year, pt.month, pt.day) == (2026, 4, 1)


def test_last_7_days() -> None:
    pf, pt = resolve_period(PeriodSpec(kind="last_7_days"), now=_now())
    assert (pt - pf).days == 7


def test_explicit_range() -> None:
    pf, pt = resolve_period(
        PeriodSpec(kind="explicit", from_date=date(2026, 4, 1), to_date=date(2026, 4, 15)),
        now=_now(),
    )
    assert pf.date() == date(2026, 4, 1) and pt.date() == date(2026, 4, 15)


def test_period_too_long_rejected() -> None:
    with pytest.raises(ValueError):
        PeriodSpec(kind="explicit", from_date=date(2020, 1, 1), to_date=date(2025, 1, 1))


def test_period_in_future_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_period(
            PeriodSpec(kind="explicit", from_date=date(2030, 1, 1), to_date=date(2030, 1, 2)),
            now=_now(),
        )
