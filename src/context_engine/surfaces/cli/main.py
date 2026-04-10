from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...app.query_service import load_store


def cmd_find_documents(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.find_documents(args.query, limit=args.limit)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_find_symbols(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.find_symbols(args.query, path_filter=args.path_filter, limit=args.limit)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_get_symbol(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.get_symbol(args.symbol)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_get_occurrences(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.get_occurrences(args.symbol, path_filter=args.path_filter, limit=args.limit)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_get_references(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.get_references(args.symbol, path_filter=args.path_filter, limit=args.limit)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_trace_semantic_path(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.trace_semantic_path(args.start_symbol, max_depth=args.max_depth, limit=args.limit)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_validate_fixture(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.validate_fixture(args.fixture_id)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_get_semantic_edges(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    provenance_filter = args.provenance if args.provenance else None
    type_filter = args.edge_type if args.edge_type else None
    out = store.get_semantic_edges(
        args.node_id,
        direction=args.direction,
        provenance_filter=provenance_filter,
        type_filter=type_filter,
        limit=args.limit,
    )
    print(json.dumps(out, indent=2, ensure_ascii=True))


def cmd_get_mixed_flow(args: argparse.Namespace) -> None:
    store = load_store(Path(args.index), force_export=args.reexport)
    out = store.get_mixed_flow(args.method_symbol)
    print(json.dumps(out, indent=2, ensure_ascii=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="context-engine")
    parser.add_argument("--index", required=True, help="Path to index.scip")
    parser.add_argument(
        "--reexport",
        action="store_true",
        help="Force regenerate NDJSON export cache",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_docs = sub.add_parser("find-documents")
    p_docs.add_argument("--query", required=True)
    p_docs.add_argument("--limit", type=int, default=20)
    p_docs.set_defaults(func=cmd_find_documents)

    p_symbols = sub.add_parser("find-symbols")
    p_symbols.add_argument("--query", required=True)
    p_symbols.add_argument("--path-filter")
    p_symbols.add_argument("--limit", type=int, default=20)
    p_symbols.set_defaults(func=cmd_find_symbols)

    p_symbol = sub.add_parser("get-symbol")
    p_symbol.add_argument("--symbol", required=True)
    p_symbol.set_defaults(func=cmd_get_symbol)

    p_occ = sub.add_parser("get-occurrences")
    p_occ.add_argument("--symbol", required=True)
    p_occ.add_argument("--path-filter")
    p_occ.add_argument("--limit", type=int, default=100)
    p_occ.set_defaults(func=cmd_get_occurrences)

    p_refs = sub.add_parser("get-references")
    p_refs.add_argument("--symbol", required=True)
    p_refs.add_argument("--path-filter")
    p_refs.add_argument("--limit", type=int, default=100)
    p_refs.set_defaults(func=cmd_get_references)

    p_trace = sub.add_parser("trace-semantic-path")
    p_trace.add_argument("--start-symbol", required=True)
    p_trace.add_argument("--max-depth", type=int, default=2)
    p_trace.add_argument("--limit", type=int, default=25)
    p_trace.set_defaults(func=cmd_trace_semantic_path)

    p_fixture = sub.add_parser("validate-fixture")
    p_fixture.add_argument("--fixture-id", required=True)
    p_fixture.set_defaults(func=cmd_validate_fixture)

    p_edges = sub.add_parser("get-semantic-edges")
    p_edges.add_argument("--node-id", required=True)
    p_edges.add_argument("--direction", choices=["in", "out", "both"], default="both")
    p_edges.add_argument("--provenance", action="append")
    p_edges.add_argument("--edge-type", action="append")
    p_edges.add_argument("--limit", type=int, default=100)
    p_edges.set_defaults(func=cmd_get_semantic_edges)

    p_flow = sub.add_parser("get-mixed-flow")
    p_flow.add_argument("--method-symbol", required=True)
    p_flow.set_defaults(func=cmd_get_mixed_flow)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
