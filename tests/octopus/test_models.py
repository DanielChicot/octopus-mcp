import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from octopus_mcp.octopus.models import (
    Account,
    ConsumptionPage,
    Product,
    ProductPage,
    UnitRate,
    UnitRatePage,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())  # type: ignore[no-any-return]


def test_parses_account() -> None:
    acc = Account.model_validate(_load("account_sample.json"))
    assert acc.number == "A-12345678"
    assert len(acc.properties) == 1
    prop = acc.properties[0]
    assert prop.electricity_meter_points[0].mpan == "1234567890123"
    assert prop.gas_meter_points[0].mprn == "9876543210"
    agreement = prop.electricity_meter_points[0].agreements[0]
    assert agreement.valid_from == datetime(2023, 1, 1, tzinfo=UTC)
    assert agreement.valid_to is None


def test_parses_consumption_page() -> None:
    page = ConsumptionPage.model_validate(_load("consumption_sample.json"))
    assert page.count == 2
    assert page.results[0].consumption == 0.234
    assert page.results[0].interval_start == datetime(2026, 4, 25, 0, 0, tzinfo=UTC)


def test_parses_product_page() -> None:
    page = ProductPage.model_validate(_load("products_sample.json"))
    assert isinstance(page.results[0], Product)
    assert page.results[0].code == "VAR-22-11-01"
    assert page.results[0].is_variable is True


def test_parses_unit_rate_page() -> None:
    page = UnitRatePage.model_validate(_load("unit_rates_sample.json"))
    assert len(page.results) == 2
    rate: UnitRate = page.results[0]
    assert rate.value_inc_vat == 26.25
    assert rate.valid_to == datetime(2026, 4, 1, tzinfo=UTC)


def test_models_reject_unknown_extra_fields_loosely() -> None:
    extra: dict[str, Any] = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
        "extra_field": "ignore me",
    }
    page = ConsumptionPage.model_validate(extra)
    assert page.count == 0
