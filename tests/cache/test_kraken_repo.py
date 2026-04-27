from datetime import UTC, datetime

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.kraken_repo import (
    KrakenRepo,
    OctoplusEventRow,
    SavingSessionRow,
)


def test_upsert_and_list_saving_sessions() -> None:
    repo = KrakenRepo(open_db(":memory:"))
    repo.upsert_saving_sessions(
        [
            SavingSessionRow(
                id="ss-1",
                code="SS-2026-01",
                starts_at=datetime(2026, 1, 12, 17, tzinfo=UTC),
                ends_at=datetime(2026, 1, 12, 18, 30, tzinfo=UTC),
                points_awarded=400,
                kwh_saved=1.7,
                joined=True,
            )
        ]
    )
    rows = repo.list_saving_sessions()
    assert rows[0].id == "ss-1"
    assert rows[0].joined is True


def test_upsert_and_list_octoplus_events() -> None:
    repo = KrakenRepo(open_db(":memory:"))
    repo.upsert_octoplus_events(
        [
            OctoplusEventRow(
                id="ev-1",
                event_type="POINTS_AWARDED",
                points=400,
                occurred_at=datetime(2026, 1, 12, tzinfo=UTC),
                payload={"reason": "saving session"},
            )
        ]
    )
    rows = repo.list_octoplus_events()
    assert rows[0].points == 400
