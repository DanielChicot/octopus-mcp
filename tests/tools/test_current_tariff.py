from datetime import UTC, datetime
from unittest.mock import MagicMock

from octopus_mcp.cache.meters import TariffAssignmentRow
from octopus_mcp.cache.rates import RateRow
from octopus_mcp.tools.current_tariff import current_tariff


async def test_current_tariff_returns_active_assignment_and_latest_rate() -> None:
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    # Return assignment for electricity, None for gas
    ctx.meters_repo.current_tariff_assignment.side_effect = lambda **k: (
        TariffAssignmentRow(
            account_number="A-1",
            fuel="electricity",
            product_code="VAR-22-11-01",
            tariff_code="E-1R-VAR-22-11-01-A",
            valid_from=datetime(2024, 1, 1, tzinfo=UTC),
            valid_to=None,
        )
        if k.get("fuel") == "electricity"
        else None
    )
    ctx.rates_repo.get_unit_rates.return_value = [
        RateRow(
            valid_from=datetime(2026, 4, 1, tzinfo=UTC),
            valid_to=None,
            value_inc_vat=25.20,
            value_exc_vat=24.0,
        ),
    ]
    ctx.rates_repo.get_standing_charges.return_value = [
        RateRow(
            valid_from=datetime(2026, 4, 1, tzinfo=UTC),
            valid_to=None,
            value_inc_vat=50.0,
            value_exc_vat=47.0,
        ),
    ]

    async def _ensure_rates(**_: object) -> None:
        return None

    ctx.ensure_rates = _ensure_rates

    out = await current_tariff(ctx=ctx, now=datetime(2026, 4, 25, tzinfo=UTC))
    elec = next(f for f in out["fuels"] if f["fuel"] == "electricity")
    assert elec["product_code"] == "VAR-22-11-01"
    assert elec["unit_rate_pence_inc_vat"] == 25.20
    assert elec["standing_charge_pence_inc_vat"] == 50.0
