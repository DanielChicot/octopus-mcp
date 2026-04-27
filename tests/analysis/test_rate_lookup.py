from datetime import UTC, datetime

from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow


def _w(start: str, end: str | None, value: float) -> RateWindow:
    s = datetime.fromisoformat(start.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None
    return RateWindow(valid_from=s, valid_to=e, value_inc_vat=value)


def test_rate_at_picks_active_window() -> None:
    stream = RateStream(
        [
            _w("2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z", 26.25),
            _w("2026-04-01T00:00:00Z", None, 25.20),
        ]
    )
    assert stream.rate_at(datetime(2026, 2, 15, tzinfo=UTC)) == 26.25
    assert stream.rate_at(datetime(2026, 4, 15, tzinfo=UTC)) == 25.20


def test_rate_at_returns_none_before_first_window() -> None:
    stream = RateStream([_w("2026-04-01T00:00:00Z", None, 25.20)])
    assert stream.rate_at(datetime(2026, 1, 1, tzinfo=UTC)) is None


def test_rate_at_open_ended_window() -> None:
    stream = RateStream([_w("2026-04-01T00:00:00Z", None, 25.20)])
    assert stream.rate_at(datetime(2030, 1, 1, tzinfo=UTC)) == 25.20


def test_unsorted_input_is_normalised() -> None:
    stream = RateStream(
        [
            _w("2026-04-01T00:00:00Z", None, 25.20),
            _w("2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z", 26.25),
        ]
    )
    assert stream.rate_at(datetime(2026, 2, 1, tzinfo=UTC)) == 26.25


def test_empty_stream_returns_none() -> None:
    assert RateStream([]).rate_at(datetime(2026, 1, 1, tzinfo=UTC)) is None
