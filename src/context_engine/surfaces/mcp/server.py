from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ... import __version__
from ...app.query_service import load_store


SERVER_INFO = {
    "name": "context-engine",
    "version": __version__,
}


def _read_message() -> dict[str, Any] | None:
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _success_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "find_documents",
            "description": "Find documents by path substring.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        },
        {
            "name": "find_symbols",
            "description": "Find symbols by display name or symbol text.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path_filter": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_symbol",
            "description": "Get summary information for a specific symbol.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                },
                "required": ["symbol"],
            },
        },
        {
            "name": "get_references",
            "description": "Get references for a specific symbol.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "path_filter": {"type": "string"},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["symbol"],
            },
        },
        {
            "name": "get_semantic_edges",
            "description": "Get derived semantic edges for a node.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "direction": {"type": "string", "enum": ["in", "out", "both"], "default": "both"},
                    "provenance_filter": {"type": "array", "items": {"type": "string"}},
                    "type_filter": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["node_id"],
            },
        },
        {
            "name": "get_mixed_flow",
            "description": "Return HTTP -> Spring -> Reactor -> Netty mixed flow for a handler method symbol.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "method_symbol": {"type": "string"},
                },
                "required": ["method_symbol"],
            },
        },
        {
            "name": "validate_fixture",
            "description": "Run pass/fail semantic validation for a named fixture.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fixture_id": {"type": "string"},
                },
                "required": ["fixture_id"],
            },
        },
    ]


def _tool_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, ensure_ascii=True),
            }
        ]
    }


def _handle_tool_call(store, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "find_documents":
        return _tool_result(store.find_documents(arguments["query"], limit=int(arguments.get("limit", 20))))
    if name == "find_symbols":
        return _tool_result(
            store.find_symbols(
                arguments["query"],
                path_filter=arguments.get("path_filter"),
                limit=int(arguments.get("limit", 20)),
            )
        )
    if name == "get_symbol":
        return _tool_result(store.get_symbol(arguments["symbol"]))
    if name == "get_references":
        return _tool_result(
            store.get_references(
                arguments["symbol"],
                path_filter=arguments.get("path_filter"),
                limit=int(arguments.get("limit", 100)),
            )
        )
    if name == "get_semantic_edges":
        return _tool_result(
            store.get_semantic_edges(
                arguments["node_id"],
                direction=arguments.get("direction", "both"),
                provenance_filter=arguments.get("provenance_filter"),
                type_filter=arguments.get("type_filter"),
                limit=int(arguments.get("limit", 100)),
            )
        )
    if name == "get_mixed_flow":
        return _tool_result(store.get_mixed_flow(arguments["method_symbol"]))
    if name == "validate_fixture":
        return _tool_result(store.validate_fixture(arguments["fixture_id"]))
    raise KeyError(f"unknown tool: {name}")


def run_server(index_path: Path, force_export: bool = False) -> None:
    store = load_store(index_path, force_export=force_export)

    while True:
        message = _read_message()
        if message is None:
            break

        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        try:
            if method == "initialize":
                _write_message(
                    _success_response(
                        request_id,
                        {
                            "protocolVersion": "2024-11-05",
                            "serverInfo": SERVER_INFO,
                            "capabilities": {"tools": {}},
                        },
                    )
                )
            elif method == "notifications/initialized":
                continue
            elif method == "ping":
                _write_message(_success_response(request_id, {}))
            elif method == "tools/list":
                _write_message(_success_response(request_id, {"tools": _tool_definitions()}))
            elif method == "tools/call":
                result = _handle_tool_call(store, params["name"], params.get("arguments", {}))
                _write_message(_success_response(request_id, result))
            else:
                _write_message(_error_response(request_id, -32601, f"Method not found: {method}"))
        except Exception as exc:  # pragma: no cover
            _write_message(_error_response(request_id, -32000, str(exc)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="context-engine-mcp")
    parser.add_argument("--index", required=True, help="Path to index.scip")
    parser.add_argument("--reexport", action="store_true", help="Force regenerate NDJSON export cache")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_server(Path(args.index), force_export=args.reexport)


if __name__ == "__main__":
    main()
