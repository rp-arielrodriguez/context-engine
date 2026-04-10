from __future__ import annotations


def build_reactor_edges(store, spring_edges: list[dict]) -> list[dict]:
    edges: list[dict] = []
    http_entrypoints_by_method: dict[str, list[str]] = {}
    for edge in spring_edges:
        if edge["type"] == "spring.endpoint_maps_to":
            http_entrypoints_by_method.setdefault(edge["target"], []).append(edge["source"])

    method_kinds = {"Method", "StaticMethod"}
    candidate_methods = [
        store.symbols_by_id[symbol]
        for symbol in store.occurrences_by_caller.keys()
        if symbol in store.symbols_by_id and store.symbols_by_id[symbol].kind in method_kinds
    ]

    for symbol in candidate_methods:
        method_occs = store._method_occurrences(symbol.symbol)
        if not method_occs:
            continue

        publisher_refs = [o for o in method_occs if store._is_reactor_publisher_symbol(o.symbol)]
        if not publisher_refs:
            continue

        publisher_types = sorted({"Flux" if "Flux#" in o.symbol else "Mono" for o in publisher_refs})
        return_stage = f"reactorstage:return:{symbol.symbol}"
        edges.append(
            {
                "source": symbol.symbol,
                "target": return_stage,
                "type": "reactor.returns_publisher",
                "provenance": "reactor-derived",
                "confidence": 0.95,
                "metadata": {
                    "document": symbol.document,
                    "method": symbol.display_name,
                    "publisher_types": publisher_types,
                },
            }
        )

        for http_node in http_entrypoints_by_method.get(symbol.symbol, []):
            edges.append(
                {
                    "source": http_node,
                    "target": return_stage,
                    "type": "reactor.http_handler_starts",
                    "provenance": "reactor-derived",
                    "confidence": 0.95,
                    "metadata": {
                        "document": symbol.document,
                        "method": symbol.display_name,
                    },
                }
            )

        operator_occs = []
        for occ in method_occs:
            operator = store._reactor_operator_name(occ.symbol)
            if operator:
                operator_occs.append((occ, operator))

        previous_stage = return_stage
        previous_operator = None
        for occ, operator in sorted(operator_occs, key=lambda item: item[0].range):
            pos = store._normalize_range(occ.range) or (0, 0, 0, 0)
            stage_id = f"reactorstage:op:{symbol.symbol}:{pos[0]}:{pos[1]}:{operator}"
            edges.append(
                {
                    "source": previous_stage,
                    "target": stage_id,
                    "type": "reactor.operator_applies",
                    "provenance": "reactor-derived",
                    "confidence": 0.9,
                    "metadata": {
                        "operator": operator,
                        "operator_symbol": occ.symbol,
                        "document": occ.document,
                        "range": occ.range,
                    },
                }
            )
            if previous_operator is not None:
                flow_type = "reactor.error_fallback_to" if operator in {"onErrorResume", "onErrorMap"} else "reactor.flows_to"
                edges.append(
                    {
                        "source": previous_operator,
                        "target": stage_id,
                        "type": flow_type,
                        "provenance": "reactor-derived",
                        "confidence": 0.85,
                        "metadata": {
                            "document": occ.document,
                            "range": occ.range,
                        },
                    }
                )
            previous_stage = stage_id
            previous_operator = stage_id

    return edges
