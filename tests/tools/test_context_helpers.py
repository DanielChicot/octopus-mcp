from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.rates import RatesRepo
from octopus_mcp.tools.context import build_helpers


async def test_ensure_rates_calls_rest_then_caches() -> None:
    conn = open_db(":memory:")
    rates_repo = RatesRepo(conn)
    rest = AsyncMock()

    class _Rate:
        def __init__(self, vf: datetime, vi: float) -> None:
            self.valid_from = vf
            self.valid_to: datetime | None = None
            self.value_inc_vat = vi
            self.value_exc_vat = vi - 1.0

    rest.get_electricity_unit_rates.return_value = [_Rate(datetime(2026, 4, 1, tzinfo=UTC), 25.0)]
    rest.get_electricity_standing_charges.return_value = [
        _Rate(datetime(2026, 4, 1, tzinfo=UTC), 50.0)
    ]

    ctx = MagicMock()
    ctx.rest = rest
    ctx.rates_repo = rates_repo
    ctx.sync_state = MagicMock()
    ctx.sync_state.is_fresh.return_value = False

    helpers = build_helpers(ctx)

    await helpers.ensure_rates(
        product_code="VAR-22-11-01", tariff_code="E-1R-VAR-22-11-01-A", fuel="electricity"
    )
    rows = rates_repo.get_unit_rates("E-1R-VAR-22-11-01-A")
    assert rows and rows[0].value_inc_vat == 25.0
