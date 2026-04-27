from datetime import UTC, datetime

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.rates import RateRow, RatesRepo


def test_upsert_and_read_unit_rates() -> None:
    repo = RatesRepo(open_db(":memory:"))
    repo.upsert_unit_rates(
        tariff_code="E-1R-VAR-22-11-01-A",
        fuel="electricity",
        rows=[
            RateRow(
                valid_from=datetime(2026, 1, 1, tzinfo=UTC),
                valid_to=datetime(2026, 4, 1, tzinfo=UTC),
                value_inc_vat=26.25,
                value_exc_vat=25.0,
            ),
            RateRow(
                valid_from=datetime(2026, 4, 1, tzinfo=UTC),
                valid_to=None,
                value_inc_vat=25.20,
                value_exc_vat=24.0,
            ),
        ],
    )
    rows = repo.get_unit_rates("E-1R-VAR-22-11-01-A")
    assert len(rows) == 2
    assert rows[0].value_inc_vat == 26.25


def test_upsert_standing_charges() -> None:
    repo = RatesRepo(open_db(":memory:"))
    repo.upsert_standing_charges(
        tariff_code="E-1R-VAR-22-11-01-A",
        fuel="electricity",
        rows=[
            RateRow(
                valid_from=datetime(2026, 1, 1, tzinfo=UTC),
                valid_to=None,
                value_inc_vat=50.0,
                value_exc_vat=47.62,
            )
        ],
    )
    rows = repo.get_standing_charges("E-1R-VAR-22-11-01-A")
    assert rows[0].value_inc_vat == 50.0
