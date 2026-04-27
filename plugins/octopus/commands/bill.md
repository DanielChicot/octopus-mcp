---
description: Show your Octopus bill summary for a period (default last_month).
argument-hint: "[period]"
---

Use the `bill_summary` MCP tool with `period.kind = "$1"` (default `last_month` if `$1` is empty).

Format the result as a markdown table:
- Columns: Fuel | kWh | Unit £ | Standing £ | Total £
- Add a final row with the grand total.
- Mention any caveats from the response in a short footnote.
- If `fuels_unavailable` is non-empty, note which fuels were skipped and why.
