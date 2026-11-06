"""Stdio protocol smoke test for the Audacity4-MCP server.

Needs no running Audacity: it checks initialize, tools/list, and that a tool
call fails cleanly when the bridge (127.0.0.1:2212) is absent. It never sends
commands to a live project. Skips if the server is not installed.

Run: python3 tests/test_audacity_mcp.py  (or pytest)
"""
import asyncio
import os
import socket
import sys
from pathlib import Path

SERVER = Path(os.environ.get("AUDACITY4_MCP_BIN", Path.home() / "Audacity4-MCP/.venv/bin/audacity4-mcp"))
PY = SERVER.parent / "python"
EXPECTED_MIN_TOOLS = 150
CORE = {"project_import_audio", "select_region", "edit_trim", "normalize", "project_export_audio"}


def _bridge_up() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", 2212)) == 0


async def _run():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=str(SERVER), args=[])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            names = {t.name for t in tools}
            result = None
            if not _bridge_up():
                # Read-only query; with no bridge it must error, not hang or crash.
                result = await asyncio.wait_for(session.call_tool("project_get_info", {}), 60)
            return init, names, result


def test_stdio_protocol():
    if not SERVER.exists():
        import pytest
        pytest.skip("audacity4-mcp not installed")
    init, names, result = asyncio.run(_run())
    assert init.serverInfo.name
    assert len(names) >= EXPECTED_MIN_TOOLS, len(names)
    assert CORE <= names, CORE - names
    if result is not None:
        assert result.isError, "call without a bridge should report an error"


if __name__ == "__main__":
    sys.path.insert(0, str(PY.parent))
    init, names, result = asyncio.run(_run())
    print(init.serverInfo.name, len(names), "tools; bridge call isError =", getattr(result, "isError", None))
    print(sorted(names)[:5], "...")
