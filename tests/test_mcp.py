from __future__ import annotations

from context_engine import __version__
from context_engine.surfaces.mcp.server import SERVER_INFO, _tool_definitions


def test_server_info_matches_package_version() -> None:
    assert SERVER_INFO["name"] == "context-engine"
    assert SERVER_INFO["version"] == __version__


def test_mcp_tool_definitions_include_core_tools() -> None:
    names = {tool["name"] for tool in _tool_definitions()}
    assert {"find_documents", "find_symbols", "get_symbol", "get_references", "get_semantic_edges", "get_mixed_flow", "validate_fixture"} <= names
