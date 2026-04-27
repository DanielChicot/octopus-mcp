---
name: octopus-analysis
description: Use when the user asks about their Octopus Energy bill, usage, tariff, or saving sessions — questions like "how much did I spend", "when do I use most electricity", "should I switch tariff", "how am I doing on saving sessions". Provides a playbook for combining the Octopus MCP tools.
---

# Octopus account analysis

When the user asks about their Octopus Energy account, use the MCP tools — never invent figures.

## Quick playbook

| User asks | Tool to call first |
|---|---|
| "How much did I spend last month?" | `bill_summary` with `period.kind = "last_month"` |
| "What did I use last week?" | `usage_breakdown` with `period.kind = "last_7_days"`, `group_by = "day"` |
| "When am I using the most electricity?" | `peak_hours` with `period.kind = "last_quarter"`, `top_n = 10` |
| "Should I switch to Tracker / Agile / Cosy / Go?" | `compare_tariff` with the relevant `target_product_code` |
| "How am I doing on saving sessions?" | `saving_session_history` |
| "What tariff am I on?" | `current_tariff` |

## Conventions

- Always state the period analysed and the units (pence inc-VAT, kWh) so the user can sanity-check.
- When a tool returns `caveats`, show them — they prevent the user being misled by simplified projections.
- For tariff comparisons, lead with the `pounds_summary` headline and put the detail underneath.
- For peak analysis, convert UTC timestamps to Europe/London (BST when applicable) before presenting.
- If the user mentions a tariff name without a code (e.g. "Tracker"), call `list_products` and pick a sensible matching `code`. If multiple match, ask the user which.
- Never speculate about Saving Sessions earnings — only report what `saving_session_history` returns.

## Things not to do

- Don't claim the user "would have saved" anything beyond the `delta_pence` returned — the model is a pure tariff swap, not a behavioural projection.
- Don't recommend Intelligent Octopus; the comparator can't model dispatches and the tool returns an error guiding to alternatives.
- Don't write to the user's Octopus account; the MCP is read-only.
