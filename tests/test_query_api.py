from __future__ import annotations

from types import SimpleNamespace

from context_engine.app.flow_helpers import field_injections_for_class
from context_engine.app.query_api import find_documents, find_symbols, get_semantic_edges, trace_semantic_path
from context_engine.core.models import DocumentRecord, SymbolRecord


def test_find_documents_filters_by_path_substring() -> None:
    store = SimpleNamespace(
        documents=[
            DocumentRecord(path="src/Foo.java", language="java", symbols_count=1, occurrences_count=1),
            DocumentRecord(path="src/Bar.kt", language="kotlin", symbols_count=1, occurrences_count=1),
        ]
    )

    result = find_documents(store, "foo")

    assert len(result) == 1
    assert result[0]["path"] == "src/Foo.java"


def test_find_symbols_uses_precomputed_search_rows_and_path_filter() -> None:
    symbol_a = SymbolRecord(
        symbol="semanticdb Foo",
        display_name="ShoppingCartController",
        enclosing_symbol="",
        kind="Class",
        document="src/a/Foo.java",
    )
    symbol_b = SymbolRecord(
        symbol="semanticdb Bar",
        display_name="ShoppingCartService",
        enclosing_symbol="",
        kind="Class",
        document="src/b/Bar.java",
    )
    store = SimpleNamespace(
        symbols=[symbol_a, symbol_b]
    )

    result = find_symbols(store, "shoppingcart", path_filter="src/a")

    assert len(result) == 1
    assert result[0]["display_name"] == "ShoppingCartController"


def test_get_semantic_edges_filters_by_direction_and_type() -> None:
    store = SimpleNamespace(
        semantic_edges_by_source={
            "node-a": [
                {"source": "node-a", "target": "node-b", "type": "spring.depends_on", "provenance": "spring-derived"},
                {"source": "node-a", "target": "node-c", "type": "reactor.flows_to", "provenance": "reactor-derived"},
            ]
        },
        semantic_edges_by_target={},
    )

    result = get_semantic_edges(store, "node-a", direction="out", type_filter=["spring.depends_on"])

    assert result == [
        {"source": "node-a", "target": "node-b", "type": "spring.depends_on", "provenance": "spring-derived"}
    ]


def test_get_semantic_edges_sorts_results_by_type_source_target() -> None:
    store = SimpleNamespace(
        semantic_edges_by_source={
            "node-a": [
                {"source": "node-a", "target": "node-c", "type": "reactor.flows_to", "provenance": "reactor-derived"},
                {"source": "node-a", "target": "node-b", "type": "spring.depends_on", "provenance": "spring-derived"},
            ]
        },
        semantic_edges_by_target={},
    )

    result = get_semantic_edges(store, "node-a", direction="out")

    assert [edge["type"] for edge in result] == ["reactor.flows_to", "spring.depends_on"]


def test_trace_semantic_path_uses_neighbors_to_expand_paths() -> None:
    store = SimpleNamespace(
        calls_out_by_symbol={
            "a": {"b"},
            "b": {"c"},
        },
        symbols_by_id={},
    )

    result = trace_semantic_path(store, "a", max_depth=2, limit=10)

    assert result[0][0]["symbol"] == "a"
    assert result[0][1]["symbol"] == "b"


def test_field_injections_for_class_reports_ambiguous_resolution() -> None:
    class_symbol = "class-a"
    field_symbol = "field-a"
    store = SimpleNamespace(
        symbols_by_id={
            class_symbol: SimpleNamespace(symbol=class_symbol, document="src/Foo.java", kind="Class", display_name="Foo"),
            field_symbol: SimpleNamespace(symbol=field_symbol, document="src/Foo.java", kind="Field", display_name="requestInfoService"),
        },
        symbols_by_document={
            "src/Foo.java": [
                SimpleNamespace(symbol=class_symbol, document="src/Foo.java", kind="Class", display_name="Foo"),
                SimpleNamespace(symbol=field_symbol, document="src/Foo.java", kind="Field", display_name="requestInfoService"),
            ]
        },
    )

    edges = [
        {
            "source": field_symbol,
            "target": "springbean:a",
            "type": "spring.injects",
            "metadata": {
                "bean_name": "requestInfoServiceImpl",
                "match_state": "ambiguous",
                "candidate_count": 2,
                "candidate_bean_names": ["getRequestInfoServiceLegacy", "requestInfoServiceImpl"],
            },
        },
        {
            "source": field_symbol,
            "target": "springbean:b",
            "type": "spring.injects",
            "metadata": {
                "bean_name": "getRequestInfoServiceLegacy",
                "match_state": "ambiguous",
                "candidate_count": 2,
                "candidate_bean_names": ["getRequestInfoServiceLegacy", "requestInfoServiceImpl"],
            },
        },
    ]

    def get_semantic_edges(node_id: str, direction: str = "both", type_filter: list[str] | None = None, limit: int = 100) -> list[dict]:
        if node_id == field_symbol and direction == "out" and type_filter == ["spring.injects"]:
            return edges[:limit]
        return []

    store.get_semantic_edges = get_semantic_edges

    result = field_injections_for_class(store, class_symbol)

    assert len(result) == 1
    assert result[0]["resolution"] == {
        "match_state": "ambiguous",
        "candidate_count": 2,
        "candidate_bean_names": ["getRequestInfoServiceLegacy", "requestInfoServiceImpl"],
    }
