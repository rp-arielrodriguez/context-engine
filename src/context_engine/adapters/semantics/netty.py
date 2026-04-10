from __future__ import annotations


def build_netty_edges(spring_edges: list[dict], reactor_edges: list[dict]) -> list[dict]:
    edges: list[dict] = []
    reactive_http_stages: list[tuple[str, str]] = []

    http_to_method = {(edge["source"], edge["target"]) for edge in spring_edges if edge["type"] == "spring.endpoint_maps_to"}
    method_to_return_stage = {
        edge["source"]: edge["target"]
        for edge in reactor_edges
        if edge["type"] == "reactor.returns_publisher"
    }

    for http_node, method_symbol in http_to_method:
        return_stage = method_to_return_stage.get(method_symbol)
        if return_stage:
            reactive_http_stages.append((http_node, return_stage))

    netty_runtime = "netty:reactor-netty:http-runtime"
    for http_node, return_stage in reactive_http_stages:
        edges.append(
            {
                "source": return_stage,
                "target": netty_runtime,
                "type": "netty.runtime_boundary",
                "provenance": "netty-derived",
                "confidence": 0.6,
                "metadata": {
                    "http_entrypoint": http_node,
                    "basis": "reactive_http_entrypoint",
                },
            }
        )

    return edges
