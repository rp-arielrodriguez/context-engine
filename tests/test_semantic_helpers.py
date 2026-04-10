from __future__ import annotations

from context_engine.adapters.semantics.helpers import (
    extract_import_map,
    is_spring_component_annotation,
    normalize_range,
    reactor_operator_name,
)


def test_normalize_range_supports_triples_and_quads() -> None:
    assert normalize_range([1, 2, 3]) == (1, 2, 1, 3)
    assert normalize_range([1, 2, 3, 4]) == (1, 2, 3, 4)
    assert normalize_range([1, 2]) is None


def test_extract_import_map_and_component_annotation_detection() -> None:
    source = "import com.example.Foo;\nimport org.springframework.stereotype.Service;\n"
    imports = extract_import_map(source)

    assert imports["Foo"] == "com.example.Foo"
    assert is_spring_component_annotation("semanticdb maven . . org/springframework/stereotype/Service#")


def test_reactor_operator_name_detects_known_operators() -> None:
    assert reactor_operator_name("semanticdb maven . . reactor/core/publisher/Mono#map().") == "map"
    assert reactor_operator_name("semanticdb maven . . reactor/core/publisher/Mono#onErrorMap(+1).") == "onErrorMap"
