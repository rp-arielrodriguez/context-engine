from __future__ import annotations

from context_engine.adapters.semantics.helpers import (
    extract_constructor_qualifier_hints,
    extract_import_map,
    extract_qualifier_hint,
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


def test_extract_qualifier_hint_finds_qualifier_annotation() -> None:
    source = (
        '    @Autowired\n'
        '    @Qualifier("mySpecialBean")\n'
        '    private SomeService someService;\n'
    )
    assert extract_qualifier_hint(source, "someService") == "mySpecialBean"


def test_extract_qualifier_hint_finds_resource_annotation() -> None:
    source = (
        '    @Resource(name = "legacyService")\n'
        '    private SomeService someService;\n'
    )
    assert extract_qualifier_hint(source, "someService") == "legacyService"


def test_extract_qualifier_hint_returns_none_when_absent() -> None:
    source = (
        '    @Autowired\n'
        '    private SomeService someService;\n'
    )
    assert extract_qualifier_hint(source, "someService") is None


def test_extract_constructor_qualifier_hints() -> None:
    source = (
        'public class MyController {\n'
        '    public MyController(\n'
        '        @Qualifier("primary") SomeService svc,\n'
        '        OtherService other\n'
        '    ) { }\n'
        '}\n'
    )
    hints = extract_constructor_qualifier_hints(source, "MyController")
    assert hints == {"svc": "primary"}
    assert "other" not in hints
