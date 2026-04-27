from datetime import UTC, datetime

import pytest

from octopus_mcp.cache.consumption import (
    ConsumptionRepo,
    ConsumptionRowIn,
)
from octopus_mcp.cache.db import open_db


@pytest.fixture
def repo() -> ConsumptionRepo:
    return ConsumptionRepo(open_db(":memory:"))


def _row(start: str, kwh: float) -> ConsumptionRowIn:
    return ConsumptionRowIn(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        interval_start=datetime.fromisoformat(start.replace("Z", "+00:00")),
        interval_end=datetime.fromisoformat(start.replace("Z", "+00:00")),
        consumption_kwh=kwh,
    )


def test_upsert_and_read_back(repo: ConsumptionRepo) -> None:
    repo.upsert([_row("2026-04-25T00:00:00Z", 0.5), _row("2026-04-25T00:30:00Z", 0.3)])
    rows = repo.get_range(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 26, tzinfo=UTC),
    )
    assert [r.consumption_kwh for r in rows] == [0.5, 0.3]


def test_upsert_is_idempotent(repo: ConsumptionRepo) -> None:
    r = _row("2026-04-25T00:00:00Z", 0.5)
    repo.upsert([r, r])
    rows = repo.get_range(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 26, tzinfo=UTC),
    )
    assert len(rows) == 1


def test_watermark_returns_max_interval_start(repo: ConsumptionRepo) -> None:
    repo.upsert([_row("2026-04-25T00:00:00Z", 0.5), _row("2026-04-26T03:00:00Z", 0.7)])
    wm = repo.latest_interval_start(fuel="electricity", mpan_or_mprn="123", serial_number="S")
    assert wm == datetime(2026, 4, 26, 3, 0, tzinfo=UTC)


def test_watermark_none_when_empty(repo: ConsumptionRepo) -> None:
    assert (
        repo.latest_interval_start(fuel="electricity", mpan_or_mprn="123", serial_number="S")
        is None
    )
