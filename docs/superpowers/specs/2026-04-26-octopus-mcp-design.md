# Octopus Energy MCP & Claude Code Plugin — Design

**Status:** Draft for review
**Date:** 2026-04-26
**Author:** Daniel Chicot (with Claude)
**License:** MIT

## Summary

A Python MCP server (`octopus-mcp`) that lets any MCP client — Claude Code, Claude Desktop, Cursor — query an Octopus Energy account: consumption, tariffs, billing math, tariff comparisons, Saving Sessions, and Octoplus history. Shipped alongside a Claude Code plugin that adds slash commands and an analysis skill on top of the MCP. Open-source, distributable via `uvx octopus-mcp` and the Claude Code plugin marketplace.

## Goals

- Read-only insight into a personal Octopus account: consumption, costs, tariffs, Saving Sessions, Octoplus.
- A killer "what if I switched tariff?" feature using actual half-hourly usage replayed against any other Octopus product.
- Snappy interactive use: results are pre-aggregated server-side so Claude doesn't burn tokens on raw half-hourly rows.
- Open-sourceable: no hard-coded secrets, multi-account-capable, runs against any Octopus account.
- Multi-front-end: MCP works standalone with Claude Desktop / Cursor / any MCP client; plugin is a Claude-Code-only convenience layer over it.

## Non-goals (v1)

- Writing data back to Octopus (no tariff switching, no enrolment changes).
- Modelling Intelligent Octopus dispatches (would need dispatch-slot history we can't reliably get).
- Background scheduled syncs / morning summaries (deferred — easy to add later via `/loop` or launchd).
- Business tariffs.
- Real-time smart-meter readings.

## User context

- Single user on Octopus **Flexible** for both electricity and gas (UK).
- Has a smart meter (we receive half-hourly data).
- Will use the MCP from both Claude Code and Claude Desktop.
- Wants the project open-sourceable so other Octopus customers can use it.

## API surface

### Octopus public REST API (`https://api.octopus.energy/v1/`)

Auth: HTTP Basic with personal API key as username, empty password.

| Endpoint | Purpose | Auth |
|---|---|---|
| `accounts/{account-number}/` | Meters, MPAN/MPRN, serials, tariff history | Yes |
| `electricity-meter-points/{MPAN}/meters/{serial}/consumption/` | Half-hourly elec consumption | Yes |
| `gas-meter-points/{MPRN}/meters/{serial}/consumption/` | Half-hourly gas consumption | Yes |
| `products/` | List of all current products | No |
| `products/{code}/` | Product detail | No |
| `products/{code}/electricity-tariffs/{tariff}/standard-unit-rates/` | Unit rates | No |
| `products/{code}/electricity-tariffs/{tariff}/standing-charges/` | Standing charges | No |
| `products/{code}/gas-tariffs/{tariff}/standard-unit-rates/` | Gas unit rates | No |
| `products/{code}/gas-tariffs/{tariff}/standing-charges/` | Gas standing charges | No |

### Kraken GraphQL (unofficial, fragile)

Auth: short-lived JWT (~1h) minted via `obtainKrakenToken` mutation using the API key.

Used only for: Saving Session enrolments and history, Octoplus event history.

Failure mode: if Kraken response shape changes, related tools fail clean with `DataError`. REST-backed tools keep working.

## Architecture

Layered modules, dependencies only flow downward.

```
┌─────────────────────────────────────────────────────────────┐
│  MCP server (server.py)                                     │
│  Registers tools, dispatches stdio JSON-RPC.                │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  tools/                                                     │
│  Thin getters + thick analysis tools.                       │
│  Each tool = one Python function, Pydantic-typed signature. │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  analysis/                                                  │
│  Pure functions: billing, tariff comparison, peaks,         │
│  aggregations. No I/O.                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  cache/                                                     │
│  SQLite store + repository functions. Owns the only path    │
│  that reads or writes the DB.                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  octopus/                                                   │
│    rest.py    — typed httpx client                          │
│    kraken.py  — GraphQL client; JWT mint + refresh          │
│    auth.py    — credential resolution                       │
│    models.py  — Pydantic API response models                │
│    errors.py  — exception hierarchy                         │
│  Owns the only path that touches the network.               │
└─────────────────────────────────────────────────────────────┘
```

The Claude Code plugin lives at the repo root (manifest, `.mcp.json`, `commands/`, `skills/` as top-level siblings of `src/`). It just *uses* the published `octopus-mcp` package — no Python code of its own.

### Boundaries

- `octopus/` is the only thing that touches the network.
- `cache/` is the only thing that touches the DB.
- `analysis/` is pure functions — no I/O at all.
- `tools/` orchestrates: cache → analysis → return.
- `server.py` only knows MCP protocol + tool registration.

## Data flow (worked example)

User types `/octopus:compare GO-VAR-22-10-14` in Claude Code:

1. Slash command `commands/compare.md` is a prompt: *"Use the `compare_tariff` MCP tool with target product `$ARGUMENTS` over the last full month. Format the result as a markdown table."*
2. Claude calls MCP tool `compare_tariff(target_product_code="GO-VAR-22-10-14", period="last_month")`.
3. `tools.compare_tariff` orchestrates:
   1. Resolve period to `(2026-03-01, 2026-04-01)` in Europe/London.
   2. Fetch consumption via `cache.get_consumption(meter, from, to)` — cache transparently syncs incremental gap from `octopus.rest` if stale.
   3. Fetch current tariff rates and target tariff rates the same way.
   4. Hand `(usage, current_rates, target_rates)` to pure `analysis.compare_tariff(...)`.
   5. Receive a `TariffComparison` Pydantic model and return it.
4. MCP serialises to JSON; Claude formats as a markdown table.

Tools always return *structured* data, not pre-formatted text — Claude can answer follow-ups ("worst day?") by inspecting the same payload without another call.

## Tools (v1 surface)

### Thick (analysis) tools

| Tool | Purpose |
|---|---|
| `bill_summary(period)` | kWh + £ per fuel, broken down by standing vs unit, VAT-inclusive |
| `usage_breakdown(period, group_by)` | Aggregations by hour/day/week/month + min/max/mean/stdev |
| `peak_hours(period, top_n)` | Top-N highest-usage half-hours |
| `compare_tariff(target_product_code, period, fuel)` | Replay actual usage against another tariff |
| `current_tariff()` | What you're on now: unit rate, standing charge, region |
| `saving_session_history()` | Octoplus saving sessions joined; points/£ earned (Kraken) |

### Thin (getter) tools

| Tool | Purpose |
|---|---|
| `get_consumption_raw(fuel, from, to, group_by)` | Pass-through to consumption endpoint |
| `list_products(filters)` | Browse Octopus product catalogue |
| `get_product(code)` | Product detail |
| `get_account()` | Account, meters, tariff history |
| `kraken_query(query, variables)` | Escape hatch for ad-hoc Kraken queries |

## Tariff comparison engine

The killer feature. Pure-function code in `analysis/tariff_comparison.py`.

### Algorithm

For each fuel:

1. Build a step-function `rate_at(timestamp)` over each rate stream. Implementation: sorted `[(valid_from, value), ...]` + binary search. Handles mid-period rate changes (Ofgem cap moves, tariff revisions, half-hourly Agile slots — all the same lookup).
2. Unit cost: `sum(row.kwh × rate_at(row.interval_start) for row in consumption)`.
3. Standing charge: count days × daily standing charge, with per-day proration on rate changes (matches Octopus billing).
4. Sum to fuel total.

Repeat for current tariff. Compose `TariffComparison`.

### Output model

```python
class FuelComparison(BaseModel):
    fuel: Literal["electricity", "gas"]
    current_unit_pence: int
    current_standing_pence: int
    current_total_pence: int
    target_unit_pence: int
    target_standing_pence: int
    target_total_pence: int
    delta_pence: int             # negative = save with target

class TariffComparison(BaseModel):
    period: tuple[date, date]
    target_product_code: str
    fuels: list[FuelComparison]
    total_current_pence: int
    total_target_pence: int
    total_delta_pence: int
    pounds_summary: str          # "Saves £12.40/mo"
    breakdown_by_day: list[DayBreakdown]
    caveats: list[str]
```

All money values are integer pence inc-VAT (no float drift).

### Always-returned caveats

- "Models a pure tariff swap; does not include Saving Sessions, Octoplus, or referral credits."
- "Assumes your usage pattern is unchanged on the target tariff. Time-of-use tariffs typically reward behaviour change — actual savings often higher."
- Region-specific: "Region X pricing applied."
- Gas: "Gas converted from m³ using calorific value 11.18 kWh/m³."

### Out of scope for v1

- Intelligent Octopus comparison (returns explicit error pointing at Cosy/Go).
- Business tariffs.
- Tariffs not currently in `products/`.

## Cache design

### Storage

SQLite via stdlib `sqlite3`, WAL mode, no ORM. Path via `platformdirs`:
- macOS: `~/Library/Caches/octopus-mcp/cache.db`
- Linux: `~/.cache/octopus-mcp/cache.db`
- Windows: `%LOCALAPPDATA%\octopus-mcp\Cache\cache.db`

Schema versioned via `PRAGMA user_version`; migrations in `cache/migrations/NNN_*.sql`.

### Schema (key tables)

```sql
CREATE TABLE consumption (
  fuel              TEXT NOT NULL,
  mpan_or_mprn      TEXT NOT NULL,
  serial_number     TEXT NOT NULL,
  interval_start    TEXT NOT NULL,    -- ISO8601 UTC
  interval_end      TEXT NOT NULL,
  consumption_kwh   REAL NOT NULL,    -- always normalised to kWh
  PRIMARY KEY (fuel, mpan_or_mprn, serial_number, interval_start)
);
CREATE INDEX idx_consumption_range ON consumption (fuel, interval_start);

CREATE TABLE unit_rates (
  tariff_code   TEXT NOT NULL,
  valid_from    TEXT NOT NULL,
  valid_to      TEXT,                 -- nullable = open-ended
  value_inc_vat REAL NOT NULL,
  value_exc_vat REAL NOT NULL,
  PRIMARY KEY (tariff_code, valid_from)
);

CREATE TABLE standing_charges (... same shape ...);

CREATE TABLE meters (account_number, fuel, mpan_or_mprn, serial_number, is_export, ...);
CREATE TABLE tariff_assignments (account_number, fuel, product_code, tariff_code, valid_from, valid_to);
CREATE TABLE products (code, display_name, brand, payload_json, fetched_at);

CREATE TABLE saving_sessions (id, code, starts_at, ends_at, points_awarded, kwh_saved, joined);
CREATE TABLE octoplus_events (id, event_type, points, occurred_at, payload_json);

CREATE TABLE sync_state (
  resource         TEXT PRIMARY KEY,  -- e.g. 'consumption:elec:1234567890'
  last_synced_at   TEXT NOT NULL,
  ttl_seconds      INTEGER            -- nullable; used by TTL resources
);
```

### Sync strategy per resource

| Resource | Strategy | Why |
|---|---|---|
| Consumption | Incremental watermark | Past data immutable; only pull the gap |
| Unit rates / standing charges | TTL 24h on rows where `valid_to IS NULL` or `valid_to > now`; permanent for rows where `valid_to <= now` | Future/current prices can change; fully-elapsed past windows can't |
| Meters / tariff assignments | TTL 7 days | Slow changing |
| Products | TTL 24h | Slow changing |
| Saving Sessions / Octoplus | Incremental by event timestamp | Immutable past |

### Gotchas (must get right)

1. **Gas units.** SMETS1 returns kWh; SMETS2 returns m³. Normalise to kWh on write using calorific value (default 39.5 MJ/m³, correction factor 1.02264 → ~11.18 kWh/m³, configurable in `config.toml`).
2. **Time zones.** API returns UTC. Store UTC. Convert to Europe/London via `zoneinfo.ZoneInfo("Europe/London")` only at the analysis/display boundary.
3. **Publication delay.** Consumption is published ~24h late. Sync always pulls "from watermark, no upper bound" — never assume "today" is available.
4. **Rate limits.** Add a polite client-side limiter (token bucket, 10 req/s) and exponential backoff on 429.
5. **Pagination.** Use `page_size=25000` (max) on consumption to minimise round-trips.

### Bypasses

- `--no-cache` server flag → all reads go live.
- `octopus-mcp resync [--resource consumption]` CLI → drop & re-pull.
- TTLs configurable in `config.toml`.

## Auth & secrets

### Two paths

- **REST:** HTTP Basic with `OCTOPUS_API_KEY` as username, empty password. Plus `OCTOPUS_ACCOUNT_NUMBER` (`A-XXXXXXXX`).
- **Kraken:** JWT (~1h TTL) minted via `obtainKrakenToken` from the API key. Cached in memory only. Auto-mint new on `UNAUTHENTICATED`. Email/password fallback opt-in (some queries require it).

### Resolution chain

1. Shell environment variables
2. `.env` file (via `python-dotenv` with `find_dotenv`; loads only if not already set)
3. OS keyring (`keyring` library, service `octopus-mcp`)
4. `~/.config/octopus-mcp/config.toml` (non-secret config only)
5. Fail with hint: `Run: octopus-mcp configure`

### Setup ergonomics

```
uv tool install octopus-mcp
octopus-mcp configure   # interactive, writes to OS keychain
# then add to .mcp.json — no secrets in the file
```

### Defensive hygiene

- `OctopusCredentials` Pydantic model has redacting `__repr__`.
- HTTP middleware strips `Authorization` headers from logs.
- Auth-failure errors never include the attempted credential.
- `.gitignore` ships with `.env`, `*.token`, `config.toml` pre-listed.
- CI has secret-scanning step (`gitleaks`).

### Multi-account (open-source posture)

All credential lookups scoped by optional `OCTOPUS_PROFILE` env var (default `"default"`). Switching profiles = restart the server with a different `OCTOPUS_PROFILE`. Multi-profile per-tool-call is v2.

## Error handling

### Exception hierarchy (`octopus/errors.py`)

```
OctopusError
├── AuthenticationError    # 401, missing/bad creds
├── AuthorizationError     # 403
├── RateLimitError         # 429, carries retry_after
├── NotFoundError          # 404, carries resource hint
├── ServiceError           # 5xx
├── DataError              # unexpected shape, partial response
├── CacheError             # SQLite issues
└── ConfigError            # missing creds, bad config
```

### Retry policy

| Failure | Retry? | How |
|---|---|---|
| 5xx | Yes | Exponential backoff, max 3 |
| 429 | Yes | Honour `Retry-After`, max 3 |
| Network/timeout | Yes | Backoff, max 3 |
| 401 (Kraken) | Yes, once | Mint new JWT, retry |
| 401 (REST) | No | Bad API key — fail fast |
| 4xx (other) | No | User error |

### MCP error surfacing

Tools convert `OctopusError` → MCP error response with structured fields:

```python
{
  "code": "rate_limited",
  "message": "Octopus API rate-limited; please retry in ~30s",
  "hint": "Reduce frequency or batch period queries",
  "retryable": True,
  "retry_after_seconds": 30
}
```

### Per-failure behaviour

- **Missing creds at startup** — server starts; every tool returns `ConfigError` with hint `"Run: octopus-mcp configure"`. Doesn't crash (clients handle dead MCPs poorly).
- **No gas meter** — gas tools return clean `NotFoundError`. `bill_summary()` degrades to electricity-only with `fuels_unavailable: ["gas"]`.
- **Empty consumption window** — returns `kwh: 0` with caveat `"No data published for N of M days"`. No error.
- **Period before account start** — clamp to account start, add caveat. No error.
- **Period in the future** — `ValidationError` at the Pydantic boundary.
- **Invalid product code** — `NotFoundError` with fuzzy-matched hint.
- **Kraken endpoint shape change** — `DataError` with truncated raw response in `data.raw_excerpt`. Tool fails clean rather than returning corrupt analysis.

### Input validation

- Pydantic models on all tool args.
- `PeriodSpec` accepts `"last_month" | "last_7_days" | "ytd" | "last_quarter" | (from, to)`.
- Period guards: max 2 years (typo protection), `from < to`, `to <= today`.

### Logging

- All logs to **stderr** (stdout reserved for MCP JSON-RPC).
- Structured JSON via stdlib logging with custom formatter.
- Level via `OCTOPUS_MCP_LOG_LEVEL` env (default `INFO`).
- Persistent log at `~/.cache/octopus-mcp/logs/server.log`, rotated 10 MB × 5 files.
- Redaction filter at formatter level: never log credentials, JWTs, full account numbers.

## Plugin (Claude Code)

`plugin/` is a thin Claude-Code packaging layer that uses the published MCP.

### Slash commands

| Command | Behaviour |
|---|---|
| `/octopus:bill [period]` | Calls `bill_summary`, formats as markdown |
| `/octopus:compare <product-code> [period]` | Calls `compare_tariff`, formats as table |
| `/octopus:peaks [period] [top_n]` | Calls `peak_hours`, formats as list |
| `/octopus:saving-sessions` | Calls `saving_session_history`, formats as table |

Each command is a thin prompt template that names the tool and the desired output shape.

### Skill

`skills/octopus-analysis/SKILL.md` — auto-triggers on natural-language energy questions (*"how much did I spend"*, *"when do I use most electricity"*, *"should I switch tariff"*). Gives Claude a playbook for combining the tools sensibly.

### `.mcp.json`

```json
{
  "mcpServers": {
    "octopus": {
      "command": "uvx",
      "args": ["octopus-mcp"]
    }
  }
}
```

## Testing strategy

| Layer | Approach | Coverage target |
|---|---|---|
| `analysis/` | Unit tests with hand-rolled fixtures. TDD. | ≥90% |
| `cache/` | In-memory SQLite (`:memory:`) | ≥85% |
| `octopus/` | `pytest-recording` cassettes. Creds scrubbed at record time. | ≥75% |
| `tools/` | Mocked `octopus/` + real in-memory cache | ≥75% |
| MCP protocol | Subprocess + JSON-RPC, smoke only | smoke |
| Live | `pytest -m live`, gated on `OCTOPUS_API_KEY`. Read-only. CI-skipped. | n/a |

### Tooling

- `pytest`, `pytest-recording`, `pytest-asyncio`, `pytest-cov`
- `ruff` (lint + format)
- `mypy --strict`
- `pre-commit`: ruff, mypy, `gitleaks`
- GitHub Actions: matrix on Python 3.11 / 3.12 / 3.13

## Packaging & release

- `pyproject.toml` with `hatchling` build backend.
- Console script: `octopus-mcp = octopus_mcp.cli:main` (subcommands: `serve` (default), `configure`, `resync`, `version`).
- Distribution: `uvx octopus-mcp` (zero install) and `pip install octopus-mcp`.
- Plugin versioned in lockstep with the Python package: `release.yml` reads `__version__` from `src/octopus_mcp/__init__.py` and writes it into `.claude-plugin/plugin.json`'s `version` field before tagging, so the two never drift.
- `release.yml`: on tag `vX.Y.Z`, publish to PyPI **and** cut a GitHub release with plugin assets attached.

## Open-source posture

- **License:** MIT.
- **README:** install paths (CC plugin, Claude Desktop manual, Cursor manual), `configure` walk-through, full tool reference, contribution guide.
- `.github/`: `ci.yml`, `release.yml`, `dependabot.yml`, issue templates, `SECURITY.md`.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant), `CHANGELOG.md` (keepachangelog).
- Conventional Commits; semver (`0.x` while pre-stable).

### Mandatory README disclaimer

> Unofficial. Not affiliated with Octopus Energy. Uses the public REST API and the community-known Kraken GraphQL endpoint; the latter is unofficial and may break without notice.

## Repo layout

```
octopus-mcp/
├── .github/                          # CI, issue templates, security
├── .claude-plugin/
│   └── plugin.json                   # the (single) plugin manifest
├── .mcp.json                         # MCP server config consumed by the plugin
├── commands/                         # plugin slash commands
│   ├── bill.md  compare.md  peaks.md  saving-sessions.md
├── skills/octopus-analysis/
│   └── SKILL.md
├── docs/superpowers/specs/
├── src/octopus_mcp/                  # the MCP package
│   ├── __init__.py    (__version__)
│   ├── cli.py         (serve | configure | resync)
│   ├── server.py      (MCP entrypoint)
│   ├── octopus/       (rest, kraken, auth, models, errors)
│   ├── cache/         (repository, migrations/)
│   ├── analysis/      (tariff_comparison, billing, aggregations, peaks)
│   └── tools/         (thin getters + thick analysis tools)
├── tests/
│   ├── unit/  integration/  e2e/  fixtures/cassettes/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md  CHANGELOG.md  CODE_OF_CONDUCT.md  SECURITY.md  LICENSE
└── pre-commit-config.yaml
```

## Out of scope (deferred)

- Background scheduled syncs — defer until v1 ships; trivial to add via `/loop` or launchd.
- Writing back to Octopus.
- Intelligent Octopus dispatch modelling.
- Business tariffs.
- v2: per-tool-call profile switching for multi-account setups.
- v2: visualisation tools (chart-spec returning).

## Open questions

None — all decisions resolved during brainstorming on 2026-04-26.
