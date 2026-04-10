from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from context_engine.adapters.runtime.source_reader import project_root_path, read_source


def test_project_root_path_supports_file_urls() -> None:
    path = project_root_path("file:///tmp/context-engine")
    assert path == Path("/tmp/context-engine")


def test_read_source_uses_cache_and_reads_from_project_root(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "Foo.java"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("class Foo {}", encoding="utf-8")

    store = SimpleNamespace(metadata=SimpleNamespace(project_root=tmp_path.as_uri()), _source_cache={})

    content = read_source(store, "src/Foo.java")
    assert content == "class Foo {}"
    assert store._source_cache["src/Foo.java"] == "class Foo {}"
