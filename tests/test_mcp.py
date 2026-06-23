"""MCP server builds and exposes the documented tools (skipped without the mcp package)."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from vitel.adapters.mcp import build_server  # noqa: E402


def test_server_builds_and_lists_tools() -> None:
    server = build_server()
    import asyncio

    tools = {t.name for t in asyncio.run(server.list_tools())}
    assert {"vitals_check", "vitals_watch", "vitals_status"} <= tools
    assert {"vitals_render", "vitals_analyze", "perceive_handoff", "doctor"} <= tools
