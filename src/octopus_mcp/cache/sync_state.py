"""Sync watermarks for incremental and TTL-based syncs."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class SyncStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def touch(self, resource: str, *, at: datetime, ttl_seconds: int | None = None) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO sync_state (resource, last_synced_at, ttl_seconds)
                VALUES (?, ?, ?)
                ON CONFLICT(resource) DO UPDATE SET
                  last_synced_at=excluded.last_synced_at,
                  ttl_seconds=excluded.ttl_seconds
                """,
                (resource, _iso(at), ttl_seconds),
            )

    def last_synced(self, resource: str) -> datetime | None:
        row = self._conn.execute(
            "SELECT last_synced_at FROM sync_state WHERE resource=?", (resource,)
        ).fetchone()
        return _parse(row["last_synced_at"]) if row else None

    def is_fresh(self, resource: str, *, now: datetime) -> bool:
        row = self._conn.execute(
            "SELECT last_synced_at, ttl_seconds FROM sync_state WHERE resource=?", (resource,)
        ).fetchone()
        if row is None or row["ttl_seconds"] is None:
            return False
        last = _parse(row["last_synced_at"])
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return (now - last) < timedelta(seconds=row["ttl_seconds"])
