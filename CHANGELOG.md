# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-27

First release.

### Added

- Async REST client for the Octopus public API: account, electricity & gas
  consumption, products, unit rates, standing charges. Basic auth, exponential
  backoff on 5xx and rate limits, structured error mapping.
- SQLite cache (WAL, atomic migrations) with five repositories:
  consumption, rates, meters + tariff assignments, products, sync state.
  Lazy incremental sync orchestrator keyed off a per-meter watermark.
- Pure-function analysis layer: rate step-function lookup, period billing
  math (integer pence), tariff comparison engine with per-day breakdown and
  caveats, time-bucket aggregations, top-N peak detection.
- Eleven MCP tools registered against `FastMCP`:
  `bill_summary`, `usage_breakdown`, `peak_hours`, `compare_tariff`,
  `current_tariff`, `saving_session_history`, plus thin getters
  (`get_account`, `list_products`, `get_product`, `get_consumption_raw`)
  and a `kraken_query` escape hatch.
- Kraken GraphQL client with JWT mint and one-shot remint on auth failure;
  Saving Sessions and Octoplus event fetchers cached per-account.
- CLI: `octopus-mcp serve | configure | resync | version`. `configure`
  stores credentials in the OS keychain via `keyring`.
- Claude Code plugin: manifest, `.mcp.json`, four slash commands, and an
  `octopus-analysis` skill that gives Claude a playbook for combining the
  tools.
- Release pipeline: tag-triggered GitHub Actions workflow that publishes to
  PyPI via OIDC trusted publishing and cuts a GitHub release with the
  plugin assets attached.

[0.1.0]: https://github.com/DanielChicot/octopus-mcp/releases/tag/v0.1.0
