from unittest.mock import AsyncMock

from octopus_mcp.octopus.models import Account, Property
from octopus_mcp.tools.thin import get_account


async def test_get_account_returns_summary_dict() -> None:
    fake_rest = AsyncMock()
    fake_rest.get_account.return_value = Account(
        number="A-12345678",
        properties=[Property(id=1, electricity_meter_points=[], gas_meter_points=[])],
    )
    out = await get_account(rest=fake_rest)
    assert out["number"] == "A-12345678"
    assert "properties" in out
