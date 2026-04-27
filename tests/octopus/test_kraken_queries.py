from unittest.mock import AsyncMock

from octopus_mcp.octopus.kraken_queries import (
    fetch_octoplus_events,
    fetch_saving_sessions,
)


async def test_fetch_saving_sessions_parses_response() -> None:
    kraken = AsyncMock()
    kraken.query.return_value = {
        "savingSessions": {
            "events": [
                {
                    "id": "ss-1",
                    "code": "SS-2026-01",
                    "startAt": "2026-01-12T17:00:00Z",
                    "endAt": "2026-01-12T18:30:00Z",
                    "octopoints": 400,
                    "kwhSaved": "1.7",
                    "joined": True,
                }
            ]
        }
    }
    rows = await fetch_saving_sessions(kraken=kraken, account_number="A-1")
    assert len(rows) == 1
    assert rows[0].id == "ss-1"
    assert rows[0].kwh_saved == 1.7
    assert rows[0].joined is True


async def test_fetch_octoplus_events_parses_response() -> None:
    kraken = AsyncMock()
    kraken.query.return_value = {
        "octoplusAccountInfo": {
            "events": [
                {
                    "id": "ev-1",
                    "type": "POINTS_AWARDED",
                    "points": 400,
                    "occurredAt": "2026-01-12T00:00:00Z",
                    "metadata": {"reason": "x"},
                }
            ]
        }
    }
    rows = await fetch_octoplus_events(kraken=kraken, account_number="A-1")
    assert rows[0].points == 400
