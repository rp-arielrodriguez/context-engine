from __future__ import annotations

from types import SimpleNamespace

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
