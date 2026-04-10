from __future__ import annotations

from types import SimpleNamespace

from context_engine.app.query_api import find_documents, get_semantic_edges
from context_engine.core.models import DocumentRecord


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
