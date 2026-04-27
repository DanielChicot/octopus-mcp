"""Lazy incremental sync orchestration for consumption."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from octopus_mcp.cache.consumption import ConsumptionRepo, ConsumptionRow, ConsumptionRowIn
from octopus_mcp.cache.sync_state import SyncStateRepo

_DEFAULT_TTL = 1800  # 30 minutes — Octopus publishes ~hourly
_log = logging.getLogger(__name__)


def _resource_key(fuel: str, mpan_or_mprn: str, serial: str) -> str:
    return f"consumption:{fuel}:{mpan_or_mprn}:{serial}"


@dataclass
class ConsumptionSyncer:
    rest: object  # OctopusRestClient — kept loose for testability
    repo: ConsumptionRepo
    state: SyncStateRepo
    ttl_seconds: int = _DEFAULT_TTL

    async def ensure(
        self,
        *,
        fuel: str,
        mpan_or_mprn: str,
        serial_number: str,
        period_from: datetime,
        period_to: datetime,
        now: datetime | None = None,
    ) -> list[ConsumptionRow]:
        now = now or datetime.now(UTC)
        key = _resource_key(fuel, mpan_or_mprn, serial_number)

        if not self.state.is_fresh(key, now=now):
            await self._fetch_gap(fuel, mpan_or_mprn, serial_number, now)
            self.state.touch(key, at=now, ttl_seconds=self.ttl_seconds)

        return self.repo.get_range(
            fuel=fuel,
            mpan_or_mprn=mpan_or_mprn,
            serial_number=serial_number,
            period_from=period_from,
            period_to=period_to,
        )

    async def _fetch_gap(self, fuel: str, mpan_or_mprn: str, serial: str, now: datetime) -> None:
        watermark = self.repo.latest_interval_start(
            fuel=fuel, mpan_or_mprn=mpan_or_mprn, serial_number=serial
        )
        # If we have a watermark, fetch from the next half-hour. Otherwise pull a year back as a sane default cap.
        from_dt = (watermark + timedelta(minutes=30)) if watermark else (now - timedelta(days=365))

        if fuel == "electricity":
            rows = await self.rest.get_electricity_consumption(  # type: ignore[attr-defined]
                mpan=mpan_or_mprn, serial=serial, period_from=from_dt
            )
        else:
            rows = await self.rest.get_gas_consumption(  # type: ignore[attr-defined]
                mprn=mpan_or_mprn, serial=serial, period_from=from_dt
            )

        if not rows:
            return

        # Known limitation: SMETS2 gas can return m³ rather than kWh.
        # Surface a warning if values look implausibly small for kWh.
        if fuel == "gas":
            for r in rows[:5]:
                if r.consumption < 0.05:
                    _log.warning(
                        "gas value looks small (%.4f); meter may report m³ not kWh — see README known limitations",
                        r.consumption,
                    )
                    break

        self.repo.upsert(
            [
                ConsumptionRowIn(
                    fuel=fuel,  # type: ignore[arg-type]
                    mpan_or_mprn=mpan_or_mprn,
                    serial_number=serial,
                    interval_start=r.interval_start,
                    interval_end=r.interval_end,
                    consumption_kwh=r.consumption,
                )
                for r in rows
            ]
        )
