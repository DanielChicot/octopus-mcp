"""Boot the MCP server in a subprocess and ensure it responds to a list_tools request.

This is shallow — it proves the binary launches and speaks the protocol; deeper
behaviour is tested at the tool/unit level.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.timeout(20)


async def test_server_responds_to_list_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OCTOPUS_API_KEY", "sk_test")
    monkeypatch.setenv("OCTOPUS_ACCOUNT_NUMBER", "A-TEST")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "octopus_mcp"],
        env={**os.environ},
    )

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.list_tools()
        names = {t.name for t in result.tools}
    expected = {"bill_summary", "compare_tariff", "current_tariff"}
    assert expected.issubset(names)
