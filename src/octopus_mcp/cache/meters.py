"""Meters and tariff assignment repository."""

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
class MeterRow:
    account_number: str
    fuel: str
    mpan_or_mprn: str
    serial_number: str
    is_export: bool = False


@dataclass(frozen=True)
class TariffAssignmentRow:
    account_number: str
    fuel: str
    product_code: str
    tariff_code: str
    valid_from: datetime
    valid_to: datetime | None


class MetersRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_meters(self, rows: list[MeterRow]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO meters (account_number, fuel, mpan_or_mprn, serial_number, is_export)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_number, fuel, mpan_or_mprn, serial_number)
                DO UPDATE SET is_export=excluded.is_export
                """,
                [
                    (r.account_number, r.fuel, r.mpan_or_mprn, r.serial_number, int(r.is_export))
                    for r in rows
                ],
            )

    def list_meters_for_account(
        self, account_number: str, *, fuel: str | None = None
    ) -> list[MeterRow]:
        if fuel is not None:
            rs = self._conn.execute(
                "SELECT * FROM meters WHERE account_number=? AND fuel=?", (account_number, fuel)
            ).fetchall()
        else:
            rs = self._conn.execute(
                "SELECT * FROM meters WHERE account_number=?", (account_number,)
            ).fetchall()
        return [
            MeterRow(
                account_number=r["account_number"],
                fuel=r["fuel"],
                mpan_or_mprn=r["mpan_or_mprn"],
                serial_number=r["serial_number"],
                is_export=bool(r["is_export"]),
            )
            for r in rs
        ]

    def upsert_tariff_assignments(self, rows: list[TariffAssignmentRow]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO tariff_assignments (account_number, fuel, product_code, tariff_code, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_number, fuel, valid_from)
                DO UPDATE SET product_code=excluded.product_code,
                              tariff_code=excluded.tariff_code,
                              valid_to=excluded.valid_to
                """,
                [
                    (
                        r.account_number,
                        r.fuel,
                        r.product_code,
                        r.tariff_code,
                        _iso(r.valid_from),
                        _iso(r.valid_to),
                    )
                    for r in rows
                ],
            )

    def current_tariff_assignment(
        self, *, account_number: str, fuel: str, at: datetime
    ) -> TariffAssignmentRow | None:
        row = self._conn.execute(
            """
            SELECT * FROM tariff_assignments
             WHERE account_number=? AND fuel=?
               AND valid_from <= ?
               AND (valid_to IS NULL OR valid_to > ?)
             ORDER BY valid_from DESC LIMIT 1
            """,
            (account_number, fuel, _iso(at), _iso(at)),
        ).fetchone()
        if row is None:
            return None
        return TariffAssignmentRow(
            account_number=row["account_number"],
            fuel=row["fuel"],
            product_code=row["product_code"],
            tariff_code=row["tariff_code"],
            valid_from=_parse(row["valid_from"]),  # type: ignore[arg-type]
            valid_to=_parse(row["valid_to"]),
        )
