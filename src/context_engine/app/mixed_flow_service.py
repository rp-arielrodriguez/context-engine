from __future__ import annotations

from .flow_helpers import class_symbol_for_method, field_injections_for_class, reactor_chain, summarize_node


def get_mixed_flow(store, method_symbol: str) -> dict:
    method = store.symbols_by_id.get(method_symbol)
    if method is None:
        raise KeyError(f"method not found: {method_symbol}")

    http_edges = store.get_semantic_edges(
        method_symbol,
        direction="in",
        type_filter=["spring.endpoint_maps_to"],
        limit=50,
    )
    class_symbol = class_symbol_for_method(store, method_symbol)
    class_summary = summarize_node(store, class_symbol) if class_symbol else None
    class_component_edges = (
        store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.component_declares"], limit=50)
        if class_symbol
        else []
    )
    class_dependency_edges = (
        store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.depends_on"], limit=200)
        if class_symbol
        else []
    )
    field_injections = field_injections_for_class(store, class_symbol) if class_symbol else []

    return_edges = store.get_semantic_edges(
        method_symbol,
        direction="out",
        type_filter=["reactor.returns_publisher"],
        limit=10,
    )
    return_stage = return_edges[0]["target"] if return_edges else ""
    operator_chain = reactor_chain(store, return_stage) if return_stage else []
    netty_edges = (
        store.get_semantic_edges(
            return_stage,
            direction="out",
            type_filter=["netty.runtime_boundary"],
            limit=20,
        )
        if return_stage
        else []
    )

    return {
        "entrypoint": {
            "method": summarize_node(store, method_symbol),
            "http_mappings": http_edges,
        },
        "spring": {
            "component": class_summary,
            "component_declares": class_component_edges,
            "field_injections": field_injections,
            "depends_on": class_dependency_edges,
        },
        "reactor": {
            "return_stage": summarize_node(store, return_stage) if return_stage else None,
            "returns_publisher": return_edges,
            "publisher_types": return_edges[0].get("metadata", {}).get("publisher_types", []) if return_edges else [],
            "operator_chain": operator_chain,
        },
        "netty": {
            "runtime_boundaries": netty_edges,
        },
    }
