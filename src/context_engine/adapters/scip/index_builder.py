from __future__ import annotations


def populate_store_indexes(store) -> None:
    store.documents_by_path = {d.path: d for d in store.documents}
    store.symbols_by_id = {s.symbol: s for s in store.symbols}
    store.occurrences_by_document = {}
    store._source_cache = {}

    store.symbols_by_document = {}
    for symbol in store.symbols:
        store.symbols_by_document.setdefault(symbol.document, []).append(symbol)

    store.occurrences_by_symbol = {}
    store.references_by_symbol = {}
    store.definitions_by_symbol = {}

    store.calls_out_by_symbol = {}
    store.calls_in_by_symbol = {}
    store.occurrences_by_caller = {}

    store.method_symbol_by_scope = {}
    store.method_scopes_by_doc = {}

    method_kinds = {"Method", "StaticMethod", "Constructor"}

    for occurrence in store.occurrences:
        if occurrence.is_definition and occurrence.kind in method_kinds and occurrence.enclosing_range:
            key = (occurrence.document, tuple(occurrence.enclosing_range))
            store.method_symbol_by_scope[key] = occurrence.symbol
            normalized = store._normalize_range(occurrence.enclosing_range)
            if normalized:
                store.method_scopes_by_doc.setdefault(occurrence.document, []).append((normalized, occurrence.symbol))

    for document in store.method_scopes_by_doc:
        store.method_scopes_by_doc[document].sort(key=lambda item: store._scope_size(item[0]))

    for occurrence in store.occurrences:
        store.occurrences_by_symbol.setdefault(occurrence.symbol, []).append(occurrence)
        store.occurrences_by_document.setdefault(occurrence.document, []).append(occurrence)
        if occurrence.is_definition:
            store.definitions_by_symbol.setdefault(occurrence.symbol, []).append(occurrence)
        else:
            store.references_by_symbol.setdefault(occurrence.symbol, []).append(occurrence)


def build_call_graph(store) -> None:
    for occurrence in store.occurrences:
        if occurrence.is_definition:
            continue
        caller = None

        if occurrence.enclosing_range:
            caller = store.method_symbol_by_scope.get((occurrence.document, tuple(occurrence.enclosing_range)))

        if caller is None:
            caller = store._infer_caller_by_position(occurrence)

        if not caller:
            continue
        callee = occurrence.symbol
        if not callee:
            continue
        if callee.startswith("local "):
            continue
        if caller == callee:
            continue
        store.occurrences_by_caller.setdefault(caller, []).append(occurrence)
        store.calls_out_by_symbol.setdefault(caller, set()).add(callee)
        store.calls_in_by_symbol.setdefault(callee, set()).add(caller)
