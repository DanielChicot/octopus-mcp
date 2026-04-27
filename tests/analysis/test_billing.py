from datetime import UTC, datetime

from octopus_mcp.analysis.billing import (
    ConsumptionPoint,
    PeriodCost,
    compute_period_cost,
)
from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow


def _r(start_iso: str, end_iso: str | None, value: float) -> RateWindow:
    s = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00")) if end_iso else None
    return RateWindow(valid_from=s, valid_to=e, value_inc_vat=value)


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_unit_cost_is_kwh_times_rate_summed_in_pence() -> None:
    consumption = [_c("2026-04-25T00:00:00Z", 1.0), _c("2026-04-25T00:30:00Z", 0.5)]
    rates = RateStream([_r("2026-04-01T00:00:00Z", None, 25.20)])
    sc_stream = RateStream([_r("2026-04-01T00:00:00Z", None, 50.0)])

    result = compute_period_cost(
        consumption=consumption,
        unit_rates=rates,
        standing_charges=sc_stream,
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 26, tzinfo=UTC),
    )
    assert isinstance(result, PeriodCost)
    # 1.5 kWh * 25.20p = 37.8p -> rounded to 38p
    assert result.unit_pence == 38
    # 1 day * 50p = 50p
    assert result.standing_pence == 50
    assert result.total_pence == 88


def test_standing_charge_prorates_over_period_in_full_days() -> None:
    rates = RateStream([_r("2026-04-01T00:00:00Z", None, 25.0)])
    sc_stream = RateStream([_r("2026-04-01T00:00:00Z", None, 60.0)])

    result = compute_period_cost(
        consumption=[],
        unit_rates=rates,
        standing_charges=sc_stream,
        period_from=datetime(2026, 4, 1, tzinfo=UTC),
        period_to=datetime(2026, 4, 8, tzinfo=UTC),
    )
    # 7 days * 60p = 420p
    assert result.standing_pence == 420


def test_consumption_outside_period_is_excluded() -> None:
    rates = RateStream([_r("2026-04-01T00:00:00Z", None, 25.0)])
    sc = RateStream([_r("2026-04-01T00:00:00Z", None, 0.0)])
    consumption = [
        _c("2026-04-24T23:30:00Z", 1.0),  # before period
        _c("2026-04-25T00:00:00Z", 2.0),  # inside
        _c("2026-04-26T00:00:00Z", 4.0),  # at boundary, exclusive
    ]
    result = compute_period_cost(
        consumption=consumption,
        unit_rates=rates,
        standing_charges=sc,
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 26, tzinfo=UTC),
    )
    # Only 2.0 kWh counted: 50p -> 50p
    assert result.unit_pence == 50


def test_missing_rate_skips_consumption_with_caveat() -> None:
    consumption = [_c("2026-04-25T00:00:00Z", 1.0)]
    rates = RateStream([])  # no rates
    sc = RateStream([])

    result = compute_period_cost(
        consumption=consumption,
        unit_rates=rates,
        standing_charges=sc,
        period_from=datetime(2026, 4, 25, tzinfo=UTC),
        period_to=datetime(2026, 4, 26, tzinfo=UTC),
    )
    assert result.unit_pence == 0
    assert any("missing rate" in c.lower() for c in result.caveats)
