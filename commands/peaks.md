---
description: Show your top-N highest-usage half-hours.
argument-hint: "[period] [top_n]"
---

Use the `peak_hours` MCP tool with:
- `period.kind = "$1"` (default `last_7_days`)
- `top_n = $2` (default `10`, must be an integer)

Format per fuel: a numbered list of half-hours with kWh, ordered descending. Convert UTC to Europe/London for display.
