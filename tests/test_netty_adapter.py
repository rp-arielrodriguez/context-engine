from __future__ import annotations

from context_engine.adapters.semantics.netty import build_netty_edges


def test_build_netty_edges_links_reactive_http_stage_to_runtime_boundary() -> None:
    spring_edges = [
        {
            "source": "http_entrypoint:doc:method:1",
            "target": "method-symbol",
            "type": "spring.endpoint_maps_to",
        }
    ]
    reactor_edges = [
        {
            "source": "method-symbol",
            "target": "reactorstage:return:method-symbol",
            "type": "reactor.returns_publisher",
        }
    ]

    edges = build_netty_edges(spring_edges, reactor_edges)

    assert len(edges) == 1
    assert edges[0]["source"] == "reactorstage:return:method-symbol"
    assert edges[0]["target"] == "netty:reactor-netty:http-runtime"
    assert edges[0]["type"] == "netty.runtime_boundary"
