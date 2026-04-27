"""Shared per-server context handed to each tool."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from octopus_mcp.cache.consumption import ConsumptionRepo
from octopus_mcp.cache.meters import MetersRepo
from octopus_mcp.cache.products import ProductsRepo
from octopus_mcp.cache.rates import RatesRepo
from octopus_mcp.cache.sync import ConsumptionSyncer
from octopus_mcp.cache.sync_state import SyncStateRepo
from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.rest import OctopusRestClient


@dataclass
class ToolContext:
    creds: OctopusCredentials
    rest: OctopusRestClient
    conn: sqlite3.Connection
    consumption_repo: ConsumptionRepo
    rates_repo: RatesRepo
    meters_repo: MetersRepo
    products_repo: ProductsRepo
    sync_state: SyncStateRepo
    consumption_syncer: ConsumptionSyncer
