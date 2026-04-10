from __future__ import annotations


def infer_caller_by_position(store, occurrence) -> str | None:
    pos = store._normalize_range(occurrence.range)
    if not pos:
        return None
    line, col = pos[0], pos[1]
    scopes = store.method_scopes_by_doc.get(occurrence.document, [])
    for scope, symbol in scopes:
        if store._contains(scope, line, col):
            return symbol
    return None


def definitions_by_document(store, document: str) -> dict[str, object]:
    out: dict[str, object] = {}
    for symbol in [record.symbol for record in store.symbols_by_document.get(document, [])]:
        defs = store.definitions_by_symbol.get(symbol, [])
        if defs:
            out[symbol] = defs[0]
    return out
