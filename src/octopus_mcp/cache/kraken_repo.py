"""Repository for Kraken-sourced data (saving sessions, octoplus events)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass(frozen=True)
class SavingSessionRow:
    id: str
    code: str | None
    starts_at: datetime
    ends_at: datetime
    points_awarded: int | None
    kwh_saved: float | None
    joined: bool


@dataclass(frozen=True)
class OctoplusEventRow:
    id: str
    event_type: str
    points: int | None
    occurred_at: datetime
    payload: dict[str, Any]


class KrakenRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_saving_sessions(self, rows: list[SavingSessionRow]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO saving_sessions
                  (id, code, starts_at, ends_at, points_awarded, kwh_saved, joined)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  code=excluded.code,
                  starts_at=excluded.starts_at,
                  ends_at=excluded.ends_at,
                  points_awarded=excluded.points_awarded,
                  kwh_saved=excluded.kwh_saved,
                  joined=excluded.joined
                """,
                [
                    (
                        r.id,
                        r.code,
                        _iso(r.starts_at),
                        _iso(r.ends_at),
                        r.points_awarded,
                        r.kwh_saved,
                        int(r.joined),
                    )
                    for r in rows
                ],
            )

    def list_saving_sessions(self) -> list[SavingSessionRow]:
        rs = self._conn.execute("SELECT * FROM saving_sessions ORDER BY starts_at").fetchall()
        return [
            SavingSessionRow(
                id=r["id"],
                code=r["code"],
                starts_at=_parse(r["starts_at"]),
                ends_at=_parse(r["ends_at"]),
                points_awarded=r["points_awarded"],
                kwh_saved=r["kwh_saved"],
                joined=bool(r["joined"]),
            )
            for r in rs
        ]

    def upsert_octoplus_events(self, rows: list[OctoplusEventRow]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO octoplus_events
                  (id, event_type, points, occurred_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  event_type=excluded.event_type,
                  points=excluded.points,
                  occurred_at=excluded.occurred_at,
                  payload_json=excluded.payload_json
                """,
                [
                    (
                        r.id,
                        r.event_type,
                        r.points,
                        _iso(r.occurred_at),
                        json.dumps(r.payload),
                    )
                    for r in rows
                ],
            )

    def list_octoplus_events(self) -> list[OctoplusEventRow]:
        rs = self._conn.execute("SELECT * FROM octoplus_events ORDER BY occurred_at").fetchall()
        return [
            OctoplusEventRow(
                id=r["id"],
                event_type=r["event_type"],
                points=r["points"],
                occurred_at=_parse(r["occurred_at"]),
                payload=json.loads(r["payload_json"]),
            )
            for r in rs
        ]
