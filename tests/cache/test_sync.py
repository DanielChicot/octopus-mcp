from datetime import UTC, datetime
from unittest.mock import AsyncMock

from octopus_mcp.cache.consumption import ConsumptionRepo, ConsumptionRowIn
from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.sync import ConsumptionSyncer
from octopus_mcp.cache.sync_state import SyncStateRepo


async def test_first_sync_pulls_full_range_and_records_watermark() -> None:
    conn = open_db(":memory:")
    repo = ConsumptionRepo(conn)
    state = SyncStateRepo(conn)

    fake_rest = AsyncMock()
    fake_rest.get_electricity_consumption.return_value = [
        type(
            "R",
            (),
            dict(
                consumption=0.5,
                interval_start=datetime(2026, 4, 25, tzinfo=UTC),
                interval_end=datetime(2026, 4, 25, 0, 30, tzinfo=UTC),
            ),
        )()
    ]
    syncer = ConsumptionSyncer(rest=fake_rest, repo=repo, state=state)

    rows = await syncer.ensure(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 26, tzinfo=UTC),
        now=datetime(2026, 4, 26, 12, tzinfo=UTC),
    )
    assert len(rows) == 1
    assert state.last_synced("consumption:electricity:123:S") is not None
    fake_rest.get_electricity_consumption.assert_awaited_once()


async def test_incremental_sync_only_fetches_after_watermark() -> None:
    conn = open_db(":memory:")
    repo = ConsumptionRepo(conn)
    state = SyncStateRepo(conn)
    repo.upsert(
        [
            ConsumptionRowIn(
                fuel="electricity",
                mpan_or_mprn="123",
                serial_number="S",
                interval_start=datetime(2026, 4, 25, tzinfo=UTC),
                interval_end=datetime(2026, 4, 25, 0, 30, tzinfo=UTC),
                consumption_kwh=0.5,
            )
        ]
    )

    fake_rest = AsyncMock()
    fake_rest.get_electricity_consumption.return_value = []
    syncer = ConsumptionSyncer(rest=fake_rest, repo=repo, state=state)

    await syncer.ensure(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 27, tzinfo=UTC),
        now=datetime(2026, 4, 27, 12, tzinfo=UTC),
    )
    call = fake_rest.get_electricity_consumption.await_args
    period_from = call.kwargs["period_from"]
    assert period_from > datetime(2026, 4, 25, tzinfo=UTC)


async def test_skip_sync_when_watermark_recent_enough() -> None:
    """If we synced within the last 30 minutes and have data, skip."""
    conn = open_db(":memory:")
    repo = ConsumptionRepo(conn)
    state = SyncStateRepo(conn)
    repo.upsert(
        [
            ConsumptionRowIn(
                fuel="electricity",
                mpan_or_mprn="123",
                serial_number="S",
                interval_start=datetime(2026, 4, 25, tzinfo=UTC),
                interval_end=datetime(2026, 4, 25, 0, 30, tzinfo=UTC),
                consumption_kwh=0.5,
            )
        ]
    )
    state.touch(
        "consumption:electricity:123:S", at=datetime(2026, 4, 27, 12, tzinfo=UTC), ttl_seconds=1800
    )

    fake_rest = AsyncMock()
    syncer = ConsumptionSyncer(rest=fake_rest, repo=repo, state=state)

    await syncer.ensure(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 25, 12, tzinfo=UTC),
        now=datetime(2026, 4, 27, 12, 15, tzinfo=UTC),
    )
    fake_rest.get_electricity_consumption.assert_not_awaited()
