from __future__ import annotations

from dataclasses import asdict


def find_documents(store, query: str, limit: int = 20) -> list[dict]:
    q = query.lower()
    out = [document for document in store.documents if q in document.path.lower()]
    out.sort(key=lambda document: document.path)
    return [asdict(document) for document in out[:limit]]


def find_symbols(store, query: str, path_filter: str | None = None, limit: int = 20) -> list[dict]:
    q = query.lower()
    path_q = path_filter.lower() if path_filter else None
    matches = []
    for symbol in store.symbols:
        if path_q and path_q not in symbol.document.lower():
            continue
        if q in symbol.display_name.lower() or q in symbol.symbol.lower():
            matches.append(symbol)
    matches.sort(key=lambda symbol: (symbol.display_name, symbol.document, symbol.symbol))
    return [asdict(symbol) for symbol in matches[:limit]]


def get_symbol(store, symbol_id: str) -> dict:
    symbol = store.symbols_by_id.get(symbol_id)
    if symbol is None:
        raise KeyError(f"symbol not found: {symbol_id}")

    occurrences = store.occurrences_by_symbol.get(symbol_id, [])
    definitions = store.definitions_by_symbol.get(symbol_id, [])
    references = store.references_by_symbol.get(symbol_id, [])

    called_symbols = sorted(store.calls_out_by_symbol.get(symbol_id, set()))
    caller_symbols = sorted(store.calls_in_by_symbol.get(symbol_id, set()))

    return {
        "symbol": asdict(symbol),
        "definitions_count": len(definitions),
        "references_count": len(references),
        "documents_count": len({occurrence.document for occurrence in occurrences}),
        "calls_out_count": len(called_symbols),
        "calls_in_count": len(caller_symbols),
    }


def get_occurrences(store, symbol_id: str, path_filter: str | None = None, limit: int = 100) -> list[dict]:
    path_q = path_filter.lower() if path_filter else None
    occurrences = store.occurrences_by_symbol.get(symbol_id, [])
    if path_q:
        occurrences = [occurrence for occurrence in occurrences if path_q in occurrence.document.lower()]
    occurrences = sorted(occurrences, key=lambda occurrence: (occurrence.document, occurrence.range))
    return [asdict(occurrence) for occurrence in occurrences[:limit]]


def get_references(store, symbol_id: str, path_filter: str | None = None, limit: int = 100) -> list[dict]:
    path_q = path_filter.lower() if path_filter else None
    references = store.references_by_symbol.get(symbol_id, [])
    if path_q:
        references = [reference for reference in references if path_q in reference.document.lower()]
    references = sorted(references, key=lambda occurrence: (occurrence.document, occurrence.range))
    return [asdict(occurrence) for occurrence in references[:limit]]


def get_semantic_edges(
    store,
    node_id: str,
    direction: str = "both",
    provenance_filter: list[str] | None = None,
    type_filter: list[str] | None = None,
    limit: int = 100,
) -> list[dict]:
    edges: list[dict] = []
    if direction in {"out", "both"}:
        edges.extend(store.semantic_edges_by_source.get(node_id, []))
    if direction in {"in", "both"}:
        edges.extend(store.semantic_edges_by_target.get(node_id, []))

    if provenance_filter:
        allowed = set(provenance_filter)
        edges = [edge for edge in edges if edge.get("provenance") in allowed]
    if type_filter:
        allowed_types = set(type_filter)
        edges = [edge for edge in edges if edge.get("type") in allowed_types]

    edges = sorted(edges, key=lambda edge: (edge["type"], edge["source"], edge["target"]))
    return edges[:limit]


def trace_semantic_path(store, start_symbol: str, max_depth: int = 2, limit: int = 25) -> list[list[dict]]:
    if max_depth < 1:
        return []

    paths: list[list[str]] = []
    queue: list[tuple[str, list[str], int]] = [(start_symbol, [start_symbol], 0)]
    visited_prefixes: set[tuple[str, ...]] = set()

    while queue and len(paths) < limit:
        current, path, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        for nxt in store._neighbors(current):
            if nxt in path:
                continue
            new_path = path + [nxt]
            prefix = tuple(new_path)
            if prefix in visited_prefixes:
                continue
            visited_prefixes.add(prefix)
            paths.append(new_path)
            queue.append((nxt, new_path, depth + 1))
            if len(paths) >= limit:
                break

    def path_to_payload(symbol_path: list[str]) -> list[dict]:
        out: list[dict] = []
        for symbol in symbol_path:
            sym = store.symbols_by_id.get(symbol)
            if sym is None:
                out.append({"symbol": symbol, "display_name": "", "document": ""})
            else:
                out.append(
                    {
                        "symbol": sym.symbol,
                        "display_name": sym.display_name,
                        "document": sym.document,
                        "kind": sym.kind,
                    }
                )
        return out

    return [path_to_payload(path) for path in paths]
