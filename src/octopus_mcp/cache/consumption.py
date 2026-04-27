"""Consumption rows: read, upsert, watermark."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass(frozen=True)
class ConsumptionRowIn:
    fuel: Literal["electricity", "gas"]
    mpan_or_mprn: str
    serial_number: str
    interval_start: datetime
    interval_end: datetime
    consumption_kwh: float


@dataclass(frozen=True)
class ConsumptionRow:
    fuel: str
    mpan_or_mprn: str
    serial_number: str
    interval_start: datetime
    interval_end: datetime
    consumption_kwh: float


class ConsumptionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, rows: Iterable[ConsumptionRowIn]) -> int:
        with self._conn:
            cur = self._conn.executemany(
                """
                INSERT INTO consumption (fuel, mpan_or_mprn, serial_number,
                                         interval_start, interval_end, consumption_kwh)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(fuel, mpan_or_mprn, serial_number, interval_start)
                DO UPDATE SET consumption_kwh = excluded.consumption_kwh,
                              interval_end = excluded.interval_end
                """,
                [
                    (
                        r.fuel,
                        r.mpan_or_mprn,
                        r.serial_number,
                        _iso(r.interval_start),
                        _iso(r.interval_end),
                        r.consumption_kwh,
                    )
                    for r in rows
                ],
            )
        return cur.rowcount

    def get_range(
        self,
        *,
        fuel: str,
        mpan_or_mprn: str,
        serial_number: str,
        period_from: datetime,
        period_to: datetime,
    ) -> list[ConsumptionRow]:
        rows = self._conn.execute(
            """
            SELECT fuel, mpan_or_mprn, serial_number,
                   interval_start, interval_end, consumption_kwh
              FROM consumption
             WHERE fuel = ? AND mpan_or_mprn = ? AND serial_number = ?
               AND interval_start >= ? AND interval_start < ?
             ORDER BY interval_start
            """,
            (fuel, mpan_or_mprn, serial_number, _iso(period_from), _iso(period_to)),
        ).fetchall()
        return [
            ConsumptionRow(
                fuel=r["fuel"],
                mpan_or_mprn=r["mpan_or_mprn"],
                serial_number=r["serial_number"],
                interval_start=_parse(r["interval_start"]),
                interval_end=_parse(r["interval_end"]),
                consumption_kwh=r["consumption_kwh"],
            )
            for r in rows
        ]

    def latest_interval_start(
        self, *, fuel: str, mpan_or_mprn: str, serial_number: str
    ) -> datetime | None:
        row = self._conn.execute(
            """
            SELECT MAX(interval_start) AS m
              FROM consumption
             WHERE fuel = ? AND mpan_or_mprn = ? AND serial_number = ?
            """,
            (fuel, mpan_or_mprn, serial_number),
        ).fetchone()
        return _parse(row["m"]) if row and row["m"] else None
