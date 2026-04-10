from __future__ import annotations

from pathlib import Path

from context_engine.adapters.scip.loader import load_records_from_ndjson


def test_load_records_from_ndjson_parses_minimal_index(tmp_path: Path) -> None:
    ndjson = tmp_path / "index.ndjson"
    ndjson.write_text(
        "\n".join(
            [
                '{"type":"meta","project_root":"file:///tmp/project","tool_name":"scip-java","tool_version":"0.1","documents_count":1,"external_symbols_count":0}',
                '{"type":"document","path":"src/Foo.java","language":"java","symbols_count":1,"occurrences_count":1}',
                '{"type":"symbol","symbol":"semanticdb maven . . foo/Foo#","display_name":"Foo","enclosing_symbol":"","kind":"Class","document":"src/Foo.java"}',
                '{"type":"occurrence","symbol":"semanticdb maven . . foo/Foo#","display_name":"Foo","enclosing_symbol":"","kind":"Class","document":"src/Foo.java","range":[1,0,1,3],"enclosing_range":[1,0,1,3],"symbol_roles":1,"roles":{"definition":true}}',
            ]
        ),
        encoding="utf-8",
    )

    metadata, documents, symbols, occurrences = load_records_from_ndjson(ndjson, lambda symbol, _: symbol)

    assert metadata.tool_name == "scip-java"
    assert documents[0].path == "src/Foo.java"
    assert symbols[0].display_name == "Foo"
    assert occurrences[0].is_definition is True
