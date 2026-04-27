"""kraken_query escape hatch for ad-hoc GraphQL."""

from __future__ import annotations

from typing import Any


async def kraken_query(
    query: str, variables: dict[str, Any] | None = None, *, ctx: Any
) -> dict[str, Any]:
    return await ctx.kraken.query(query, variables or {})  # type: ignore[no-any-return]
