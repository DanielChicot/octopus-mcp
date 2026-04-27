from pathlib import Path

from octopus_mcp.cache.db import open_db, run_migrations


def test_open_db_in_memory_runs_migrations() -> None:
    conn = open_db(":memory:")
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    expected = {
        "consumption",
        "unit_rates",
        "standing_charges",
        "meters",
        "tariff_assignments",
        "products",
        "saving_sessions",
        "octoplus_events",
        "sync_state",
    }
    assert expected.issubset(tables)


def test_user_version_advances_after_migration() -> None:
    conn = open_db(":memory:")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version >= 1


def test_running_migrations_twice_is_idempotent() -> None:
    conn = open_db(":memory:")
    run_migrations(conn)  # second invocation
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version >= 1


def test_wal_mode_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = open_db(str(db_path))
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"
