"""SQLite connection + migration runner."""

from __future__ import annotations

import sqlite3
from importlib import resources

from octopus_mcp.cache import migrations as migrations_pkg


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn)
    return conn


def _list_migrations() -> list[tuple[int, str]]:
    files: list[tuple[int, str]] = []
    for entry in resources.files(migrations_pkg).iterdir():
        name = entry.name
        if name.endswith(".sql"):
            num = int(name.split("_", 1)[0])
            files.append((num, entry.read_text(encoding="utf-8")))
    files.sort()
    return files


def run_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, sql in _list_migrations():
        if version <= current:
            continue
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {version}")
