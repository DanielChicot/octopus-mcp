"""Product catalogue repository."""

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


@dataclass(frozen=True)
class ProductRow:
    code: str
    display_name: str
    brand: str | None
    payload: dict[str, Any]
    fetched_at: datetime


class ProductsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, rows: list[ProductRow]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO products (code, display_name, brand, payload_json, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                  display_name=excluded.display_name,
                  brand=excluded.brand,
                  payload_json=excluded.payload_json,
                  fetched_at=excluded.fetched_at
                """,
                [
                    (r.code, r.display_name, r.brand, json.dumps(r.payload), _iso(r.fetched_at))
                    for r in rows
                ],
            )

    def list_all(self) -> list[ProductRow]:
        rs = self._conn.execute("SELECT * FROM products ORDER BY code").fetchall()
        return [self._row(r) for r in rs]

    def get_by_code(self, code: str) -> ProductRow | None:
        r = self._conn.execute("SELECT * FROM products WHERE code=?", (code,)).fetchone()
        return self._row(r) if r else None

    @staticmethod
    def _row(r: sqlite3.Row) -> ProductRow:
        return ProductRow(
            code=r["code"],
            display_name=r["display_name"],
            brand=r["brand"],
            payload=json.loads(r["payload_json"]),
            fetched_at=datetime.fromisoformat(r["fetched_at"].replace("Z", "+00:00")),
        )
