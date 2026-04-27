"""SQLite connection + migration runner."""

from __future__ import annotations

import re
import sqlite3
from importlib import resources
from pathlib import Path

from octopus_mcp.cache import migrations as migrations_pkg

_MIGRATION_RE = re.compile(r"^(\d+)_[a-z][a-z0-9_]*\.sql$")


def open_db(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # PRAGMAs are run outside any transaction
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn)
    return conn


def _list_migrations() -> list[tuple[int, str]]:
    files: list[tuple[int, str]] = []
    seen: set[int] = set()
    for entry in resources.files(migrations_pkg).iterdir():
        m = _MIGRATION_RE.match(entry.name)
        if not m:
            continue
        num = int(m.group(1))
        if num in seen:
            raise RuntimeError(f"Duplicate migration version {num}")
        seen.add(num)
        files.append((num, entry.read_text(encoding="utf-8")))
    files.sort()
    return files


def _split_sql(sql: str) -> list[str]:
    """Naive splitter: SQLite migrations don't use procedural blocks, so
    splitting on ';' boundaries (preserving non-empty statements) is enough.

    Comments are stripped line-by-line before checking whether a chunk is
    empty, so a leading comment block does not swallow the first statement.
    """
    out: list[str] = []
    for raw in sql.split(";"):
        # Drop comment-only lines and re-join to find the real SQL content.
        code_lines = [line for line in raw.splitlines() if not line.strip().startswith("--")]
        code = "\n".join(code_lines).strip()
        if code:
            out.append(code)
    return out


def run_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, sql in _list_migrations():
        if version <= current:
            continue
        conn.execute("BEGIN")
        try:
            for statement in _split_sql(sql):
                conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
