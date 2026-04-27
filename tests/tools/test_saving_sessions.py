from datetime import UTC, datetime
from unittest.mock import MagicMock

from octopus_mcp.cache.kraken_repo import OctoplusEventRow, SavingSessionRow
from octopus_mcp.tools.saving_sessions import saving_session_history


async def test_saving_session_history_returns_combined_view() -> None:
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.kraken_repo.list_saving_sessions.return_value = [
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
    ctx.kraken_repo.list_octoplus_events.return_value = [
        OctoplusEventRow(
            id="ev-1",
            event_type="POINTS_AWARDED",
            points=400,
            occurred_at=datetime(2026, 1, 12, tzinfo=UTC),
            payload={},
        )
    ]

    async def _ensure_kraken_synced() -> None:
        return None

    ctx.ensure_kraken_synced = _ensure_kraken_synced

    out = await saving_session_history(ctx=ctx)
    assert len(out["sessions"]) == 1
    assert out["totals"]["points_awarded"] == 400
    assert out["totals"]["sessions_joined"] == 1
