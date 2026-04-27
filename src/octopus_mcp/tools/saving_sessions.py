"""saving_session_history thick tool."""

from __future__ import annotations

from typing import Any


async def saving_session_history(*, ctx: Any) -> dict[str, Any]:
    await ctx.ensure_kraken_synced()
    sessions = ctx.kraken_repo.list_saving_sessions()
    events = ctx.kraken_repo.list_octoplus_events()

    points_total = sum(s.points_awarded or 0 for s in sessions if s.joined)
    kwh_total = sum(s.kwh_saved or 0.0 for s in sessions if s.joined)

    return {
        "sessions": [
            {
                "id": s.id,
                "code": s.code,
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat(),
                "joined": s.joined,
                "points_awarded": s.points_awarded,
                "kwh_saved": s.kwh_saved,
            }
            for s in sessions
        ],
        "octoplus_events": [
            {
                "id": e.id,
                "type": e.event_type,
                "points": e.points,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "totals": {
            "sessions_total": len(sessions),
            "sessions_joined": sum(1 for s in sessions if s.joined),
            "points_awarded": points_total,
            "kwh_saved": round(kwh_total, 3),
        },
    }
