from datetime import UTC, datetime, timedelta

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.sync_state import SyncStateRepo


def test_set_and_get_watermark() -> None:
    repo = SyncStateRepo(open_db(":memory:"))
    now = datetime(2026, 4, 25, tzinfo=UTC)
    repo.touch("products", at=now, ttl_seconds=86400)
    assert repo.last_synced("products") == now


def test_is_fresh_within_ttl() -> None:
    repo = SyncStateRepo(open_db(":memory:"))
    now = datetime(2026, 4, 25, tzinfo=UTC)
    repo.touch("products", at=now, ttl_seconds=3600)
    assert repo.is_fresh("products", now=now + timedelta(minutes=30)) is True
    assert repo.is_fresh("products", now=now + timedelta(hours=2)) is False


def test_is_fresh_returns_false_when_unknown() -> None:
    repo = SyncStateRepo(open_db(":memory:"))
    assert repo.is_fresh("never-synced", now=datetime.now(UTC)) is False
