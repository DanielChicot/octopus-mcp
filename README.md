# octopus-mcp

[![PyPI](https://img.shields.io/pypi/v/octopus-mcp.svg)](https://pypi.org/project/octopus-mcp/)
[![CI](https://github.com/DanielChicot/octopus-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/DanielChicot/octopus-mcp/actions/workflows/ci.yml)

> Unofficial. Not affiliated with Octopus Energy. Uses the public REST API and the community-known Kraken GraphQL endpoint; the latter is unofficial and may break without notice.

A Model Context Protocol server that lets Claude analyse your Octopus Energy account: usage, costs, tariff comparisons, Saving Sessions, Octoplus rewards.

Works with **Claude Code**, **Claude Desktop**, and any MCP-compatible client.

## Prerequisites

- **Python 3.11 or newer**
- An **Octopus Energy** account in the UK
- A **smart meter** sending half-hourly readings (so consumption data is available via the API)

## Install

The server is published on PyPI as [`octopus-mcp`](https://pypi.org/project/octopus-mcp/). You can install it with [`uv`](https://docs.astral.sh/uv/) (recommended) or plain `pip`.

### With `uv` (recommended)

If you don't have `uv` yet:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then install the MCP server and save credentials:

```bash
uv tool install octopus-mcp
octopus-mcp configure   # interactive; writes to your OS keychain
```

### With `pip`

```bash
pip install octopus-mcp
octopus-mcp configure
```

### Wire it into your MCP client

#### Claude Code

```bash
# In Claude Code, install the plugin from this repo:
/plugin install DanielChicot/octopus-mcp
```

The plugin includes the MCP config and four slash commands (`/octopus:bill`, `/octopus:compare`, `/octopus:peaks`, `/octopus:saving-sessions`).

#### Claude Desktop, Cursor, and other MCP clients

Add this entry to your client's MCP config:

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

(If you installed with `pip` instead of `uv`, replace `"command": "uvx", "args": ["octopus-mcp"]` with `"command": "octopus-mcp", "args": ["serve"]`.)

The config file lives at:

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Restart your MCP client after editing the config.

## Credentials

You need:

- `OCTOPUS_API_KEY` — find at [octopus.energy → My account → Personal details → Developer settings](https://octopus.energy/dashboard/new/accounts/personal-details/api-access)
- `OCTOPUS_ACCOUNT_NUMBER` — `A-XXXXXXXX`, on any bill or in your account

Optional (only some Kraken queries):

- `OCTOPUS_EMAIL` / `OCTOPUS_PASSWORD`

Resolution order: shell env > `.env` > OS keyring > error. The recommended path is `octopus-mcp configure` which writes to the OS keyring so secrets never sit in plaintext config.

## Tools

| Tool | What it does |
|---|---|
| `bill_summary(period)` | Total kWh and £ per fuel for a period |
| `usage_breakdown(period, group_by)` | Aggregated kWh by hour/day/week/month |
| `peak_hours(period, top_n)` | Top-N highest-usage half-hours |
| `compare_tariff(target_product_code, period, fuel)` | Replay your usage against another Octopus tariff |
| `current_tariff()` | What you're on now: unit rate, standing charge |
| `saving_session_history()` | Octoplus saving sessions joined and rewards earned |
| `get_account()`, `list_products()`, `get_product()`, `get_consumption_raw()`, `kraken_query()` | Thin getters / escape hatches |

## Slash commands (Claude Code plugin)

- `/octopus:bill [period]` — bill summary as a markdown table
- `/octopus:compare <product-code> [period]` — tariff comparison with caveats
- `/octopus:peaks [period] [top_n]` — highest-usage half-hours
- `/octopus:saving-sessions` — Octoplus history

## How it works

- A SQLite cache at `~/Library/Caches/octopus-mcp/` (or your platform's equivalent) holds your historical consumption and tariff data, refreshed incrementally.
- All cost figures are in integer pence inc-VAT (no float drift), with a derived pounds string for display.
- Tariff comparison is a *pure tariff swap* model — caveats list what it does and doesn't model. See the design doc.

## Known limitations (v0.1)

- **Gas SMETS2 m³ vs kWh:** if your gas meter reports in m³, values won't be normalised — expect implausibly small numbers and multiply by ~11.18 to convert. v0.2 will detect and apply calorific conversion automatically.
- **Region-aware tariff lookup:** `compare_tariff` currently picks the first region's tariff variant from a target product. v0.2 will use your postcode-derived region.
- **TTLs are hardcoded:** no `config.toml` support yet.
- **No background sync:** consumption is fetched lazily on demand.

## Privacy

The MCP runs on your machine. No data leaves your computer except direct calls to `api.octopus.energy`. Credentials live in your OS keychain. Logs at `~/Library/Logs/octopus-mcp/server.log` redact secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `pre-commit run --all-files` before pushing.

## License

MIT — see [LICENSE](LICENSE).
