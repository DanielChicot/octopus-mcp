from datetime import UTC, datetime

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.products import ProductRow, ProductsRepo


def test_upsert_and_list_products() -> None:
    repo = ProductsRepo(open_db(":memory:"))
    repo.upsert(
        [
            ProductRow(
                code="VAR-22-11-01",
                display_name="Flexible",
                brand="OE",
                payload={"foo": "bar"},
                fetched_at=datetime(2026, 4, 25, tzinfo=UTC),
            ),
        ]
    )
    products = repo.list_all()
    assert products[0].code == "VAR-22-11-01"
    assert products[0].payload == {"foo": "bar"}


def test_get_by_code_returns_none_when_missing() -> None:
    repo = ProductsRepo(open_db(":memory:"))
    assert repo.get_by_code("MISSING") is None
