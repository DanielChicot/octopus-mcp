from datetime import UTC, datetime

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.meters import MeterRow, MetersRepo, TariffAssignmentRow


def test_upsert_and_list_meters() -> None:
    repo = MetersRepo(open_db(":memory:"))
    repo.upsert_meters(
        [
            MeterRow(
                account_number="A-1",
                fuel="electricity",
                mpan_or_mprn="111",
                serial_number="ELEC",
                is_export=False,
            ),
            MeterRow(
                account_number="A-1",
                fuel="gas",
                mpan_or_mprn="999",
                serial_number="GAS",
                is_export=False,
            ),
        ]
    )
    elec = repo.list_meters_for_account("A-1", fuel="electricity")
    assert len(elec) == 1 and elec[0].mpan_or_mprn == "111"


def test_upsert_and_query_tariff_assignments() -> None:
    repo = MetersRepo(open_db(":memory:"))
    repo.upsert_tariff_assignments(
        [
            TariffAssignmentRow(
                account_number="A-1",
                fuel="electricity",
                product_code="VAR-22-11-01",
                tariff_code="E-1R-VAR-22-11-01-A",
                valid_from=datetime(2024, 1, 1, tzinfo=UTC),
                valid_to=None,
            )
        ]
    )
    current = repo.current_tariff_assignment(
        account_number="A-1", fuel="electricity", at=datetime(2026, 4, 25, tzinfo=UTC)
    )
    assert current is not None and current.tariff_code == "E-1R-VAR-22-11-01-A"
