"""Concrete Kraken queries used by the MCP.

Field names (startAt, endAt, octopoints, kwhSaved, occurredAt, etc.) are
community-known from the Octopus Kraken API and may need adjustment if they
don't match prod — that's why parsing logic lives here, so fields can be
updated without re-architecting the rest of the system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from octopus_mcp.cache.kraken_repo import OctoplusEventRow, SavingSessionRow

_SAVING_SESSIONS_QUERY = """
query SavingSessions($acct: String!) {
  savingSessions(accountNumber: $acct) {
    events {
      id code startAt endAt octopoints kwhSaved joined
    }
  }
}
"""

_OCTOPLUS_QUERY = """
query OctoplusEvents($acct: String!) {
  octoplusAccountInfo(accountNumber: $acct) {
    events {
      id type points occurredAt metadata
    }
  }
}
"""


def _parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


async def fetch_saving_sessions(*, kraken: Any, account_number: str) -> list[SavingSessionRow]:
    data = await kraken.query(_SAVING_SESSIONS_QUERY, {"acct": account_number})
    events = (data.get("savingSessions") or {}).get("events") or []
    out: list[SavingSessionRow] = []
    for e in events:
        out.append(
            SavingSessionRow(
                id=str(e["id"]),
                code=e.get("code"),
                starts_at=_parse_dt(e["startAt"]),
                ends_at=_parse_dt(e["endAt"]),
                points_awarded=e.get("octopoints"),
                kwh_saved=float(e["kwhSaved"]) if e.get("kwhSaved") is not None else None,
                joined=bool(e.get("joined", False)),
            )
        )
    return out


async def fetch_octoplus_events(*, kraken: Any, account_number: str) -> list[OctoplusEventRow]:
    data = await kraken.query(_OCTOPLUS_QUERY, {"acct": account_number})
    events = (data.get("octoplusAccountInfo") or {}).get("events") or []
    return [
        OctoplusEventRow(
            id=str(e["id"]),
            event_type=str(e["type"]),
            points=e.get("points"),
            occurred_at=_parse_dt(e["occurredAt"]),
            payload=e.get("metadata") or {},
        )
        for e in events
    ]
