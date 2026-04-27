# octopus-mcp

> Unofficial. Not affiliated with Octopus Energy. Uses the public REST API and the community-known Kraken GraphQL endpoint; the latter is unofficial and may break without notice.

A Model Context Protocol server that lets Claude analyse your Octopus Energy account: usage, costs, tariff comparisons, Saving Sessions, Octoplus rewards.

Works with **Claude Code**, **Claude Desktop**, and any MCP-compatible client.

## Install

### Claude Code (recommended)

```bash
# 1. Install the MCP server
uv tool install octopus-mcp

# 2. Save your credentials in your OS keychain
octopus-mcp configure

# 3. Install the plugin from this repo (in Claude Code):
/plugin install DanielChicot/octopus-mcp
```

### Claude Desktop / Cursor / other MCP clients

Install the server, configure credentials, then add to your MCP client config:

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

For Claude Desktop, the config lives at `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

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
