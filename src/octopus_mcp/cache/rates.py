"""Tariff unit-rate and standing-charge repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _parse(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


@dataclass(frozen=True)
class RateRow:
    valid_from: datetime
    valid_to: datetime | None
    value_inc_vat: float
    value_exc_vat: float


class RatesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_unit_rates(self, *, tariff_code: str, fuel: str, rows: list[RateRow]) -> None:
        self._upsert("unit_rates", tariff_code, fuel, rows)

    def upsert_standing_charges(self, *, tariff_code: str, fuel: str, rows: list[RateRow]) -> None:
        self._upsert("standing_charges", tariff_code, fuel, rows)

    def _upsert(self, table: str, tariff_code: str, fuel: str, rows: list[RateRow]) -> None:
        with self._conn:
            self._conn.executemany(
                f"""
                INSERT INTO {table} (tariff_code, fuel, valid_from, valid_to, value_inc_vat, value_exc_vat)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tariff_code, valid_from)
                DO UPDATE SET valid_to=excluded.valid_to,
                              value_inc_vat=excluded.value_inc_vat,
                              value_exc_vat=excluded.value_exc_vat,
                              fuel=excluded.fuel
                """,
                [
                    (
                        tariff_code,
                        fuel,
                        _iso(r.valid_from),
                        _iso(r.valid_to),
                        r.value_inc_vat,
                        r.value_exc_vat,
                    )
                    for r in rows
                ],
            )

    def get_unit_rates(self, tariff_code: str) -> list[RateRow]:
        return self._select("unit_rates", tariff_code)

    def get_standing_charges(self, tariff_code: str) -> list[RateRow]:
        return self._select("standing_charges", tariff_code)

    def _select(self, table: str, tariff_code: str) -> list[RateRow]:
        rows = self._conn.execute(
            f"SELECT valid_from, valid_to, value_inc_vat, value_exc_vat FROM {table} WHERE tariff_code=? ORDER BY valid_from",
            (tariff_code,),
        ).fetchall()
        return [
            RateRow(
                valid_from=_parse(r["valid_from"]),  # type: ignore[arg-type]
                valid_to=_parse(r["valid_to"]),
                value_inc_vat=r["value_inc_vat"],
                value_exc_vat=r["value_exc_vat"],
            )
            for r in rows
        ]
