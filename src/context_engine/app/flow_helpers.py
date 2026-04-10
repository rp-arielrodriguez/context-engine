from __future__ import annotations


def summarize_node(store, node_id: str) -> dict:
    sym = store.symbols_by_id.get(node_id)
    if sym is not None:
        return {
            "id": node_id,
            "kind": sym.kind,
            "display_name": sym.display_name,
            "document": sym.document,
        }
    if node_id.startswith("http_entrypoint:"):
        parts = node_id.split(":", 3)
        return {
            "id": node_id,
            "kind": "http_entrypoint",
            "document": parts[1] if len(parts) > 1 else "",
            "display_name": parts[2] if len(parts) > 2 else node_id,
        }
    if node_id.startswith("reactorstage:"):
        return {
            "id": node_id,
            "kind": "reactive_stage",
            "display_name": node_id,
            "document": "",
        }
    if node_id.startswith("springbean:"):
        return {
            "id": node_id,
            "kind": "spring_bean",
            "display_name": node_id,
            "document": "",
        }
    if node_id.startswith("netty:"):
        return {
            "id": node_id,
            "kind": "netty_component",
            "display_name": node_id,
            "document": "",
        }
    return {"id": node_id, "kind": "unknown", "display_name": node_id, "document": ""}


def class_symbol_for_method(store, method_symbol: str) -> str | None:
    method = store.symbols_by_id.get(method_symbol)
    if method is None:
        return None
    classes = [symbol for symbol in store.symbols_by_document.get(method.document, []) if symbol.kind == "Class"]
    return classes[0].symbol if classes else None


def _spring_injection_resolution(edges: list[dict]) -> dict:
    if not edges:
        return {
            "match_state": "unresolved",
            "candidate_count": 0,
            "candidate_bean_names": [],
        }

    metadata = edges[0].get("metadata", {})
    bean_names = sorted(
        {
            edge.get("metadata", {}).get("bean_name", "")
            for edge in edges
            if edge.get("metadata", {}).get("bean_name")
        }
    )
    candidate_names = metadata.get("candidate_bean_names") or bean_names
    return {
        "match_state": metadata.get("match_state", "resolved" if len(edges) == 1 else "ambiguous"),
        "candidate_count": metadata.get("candidate_count", len(edges)),
        "candidate_bean_names": candidate_names,
    }


def field_injections_for_class(store, class_symbol: str) -> list[dict]:
    class_node = store.symbols_by_id.get(class_symbol)
    if class_node is None:
        return []
    fields = [
        symbol
        for symbol in store.symbols_by_document.get(class_node.document, [])
        if symbol.kind == "Field" and store.get_semantic_edges(symbol.symbol, direction="out", type_filter=["spring.injects"])
    ]
    out = []
    for field in fields:
        edges = store.get_semantic_edges(field.symbol, direction="out", type_filter=["spring.injects"], limit=100)
        out.append(
            {
                "field": summarize_node(store, field.symbol),
                "injects": edges,
                "resolution": _spring_injection_resolution(edges),
            }
        )
    return out


def reactor_chain(store, return_stage: str) -> list[dict]:
    seen: set[str] = set()
    queue = [return_stage]
    stages: dict[str, dict] = {}
    allowed = {"reactor.operator_applies", "reactor.flows_to", "reactor.error_fallback_to"}

    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.add(node)
        for edge in store.get_semantic_edges(node, direction="out", type_filter=list(allowed), limit=500):
            target = edge["target"]
            metadata = edge.get("metadata", {})
            if target.startswith("reactorstage:"):
                stages[target] = {
                    "node": summarize_node(store, target),
                    "via": edge["type"],
                    "operator": metadata.get("operator", ""),
                    "flow_kind": edge["type"],
                    "publisher_type": "Flux" if "Flux#" in metadata.get("operator_symbol", "") else "Mono",
                    "range": metadata.get("range", []),
                }
                if target not in seen:
                    queue.append(target)

    def sort_key(item: dict) -> tuple:
        rng = item.get("range") or []
        return (rng[0], rng[1]) if len(rng) >= 2 else (999999, 999999)

    return sorted(stages.values(), key=sort_key)


def has_operator(store, return_stage: str, operator_name: str) -> bool:
    seen: set[str] = set()
    queue = [return_stage]
    allowed_types = {"reactor.operator_applies", "reactor.flows_to", "reactor.error_fallback_to"}

    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.add(node)

        edges = store.get_semantic_edges(node, direction="out", type_filter=list(allowed_types), limit=500)
        for edge in edges:
            if edge.get("metadata", {}).get("operator") == operator_name:
                return True
            target = edge.get("target")
            if target and target not in seen:
                queue.append(target)

    return False
