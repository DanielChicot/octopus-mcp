"""Tests for the MCP server entrypoint."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from octopus_mcp.server import _build_app


def test_build_app_registers_expected_tools() -> None:
    app, ctx = _build_app(test_mode=True)
    assert ctx is None
    names = _list_registered_tool_names(app)
    expected = {
        "bill_summary",
        "current_tariff",
        "usage_breakdown",
        "peak_hours",
        "compare_tariff",
        "get_account",
        "list_products",
        "get_product",
        "get_consumption_raw",
        "saving_session_history",
        "kraken_query",
    }
    assert expected.issubset(names)


def _list_registered_tool_names(app: FastMCP) -> set[str]:
    """Return the set of registered tool names from a FastMCP app."""
    if hasattr(app, "list_tools_sync"):
        return {t.name for t in app.list_tools_sync()}
    if hasattr(app, "_tool_manager"):
        # FastMCP modern: _tool_manager._tools is a dict[name, Tool]
        return set(app._tool_manager._tools.keys())
    if hasattr(app, "_tools"):
        return set(app._tools.keys())
    raise RuntimeError("Cannot find registered tools on app")
