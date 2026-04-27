---
description: Compare your current tariff against another Octopus product.
argument-hint: "<product-code> [period]"
---

Use the `compare_tariff` MCP tool with:
- `target_product_code = "$1"`
- `period.kind = "$2"` (default `last_month`)
- `fuel = "both"`

Format:
- Top line: the `pounds_summary` field, prominent.
- Per-fuel table: Fuel | Current £ | Target £ | Delta £.
- Show the per-day breakdown as a small markdown table beneath, sorted by date.
- List every entry in `caveats[]` as bullets at the end. Do NOT hide them.
- If the tool returns an error mentioning Intelligent Octopus, suggest trying `GO-VAR-22-10-14` or `COSY-22-12-08` instead.
