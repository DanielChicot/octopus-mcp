"""Period specification + resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

PeriodKind = Literal["last_month", "last_7_days", "last_quarter", "ytd", "explicit"]


@dataclass(frozen=True)
class PeriodSpec:
    kind: PeriodKind
    from_date: date | None = None
    to_date: date | None = None

    def __post_init__(self) -> None:
        if self.kind == "explicit":
            if self.from_date is None or self.to_date is None:
                raise ValueError("explicit period requires from_date and to_date")
            if self.from_date >= self.to_date:
                raise ValueError("from_date must be before to_date")
            if (self.to_date - self.from_date).days > 366 * 2:
                raise ValueError("period exceeds maximum of 2 years")


def _start_of(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def resolve_period(spec: PeriodSpec, *, now: datetime) -> tuple[datetime, datetime]:
    if spec.kind == "last_7_days":
        end = _start_of(now.date())
        return end - timedelta(days=7), end
    if spec.kind == "last_month":
        first_this = now.date().replace(day=1)
        last_first = (first_this - timedelta(days=1)).replace(day=1)
        return _start_of(last_first), _start_of(first_this)
    if spec.kind == "last_quarter":
        end = _start_of(now.date().replace(day=1))
        m = end.month - 3
        y = end.year
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=UTC)
        return start, end
    if spec.kind == "ytd":
        return datetime(now.year, 1, 1, tzinfo=UTC), _start_of(now.date())
    if spec.kind == "explicit":
        assert spec.from_date and spec.to_date
        if _start_of(spec.to_date) > now:
            raise ValueError("period extends into the future")
        return _start_of(spec.from_date), _start_of(spec.to_date)
    raise ValueError(f"unknown PeriodKind: {spec.kind}")
