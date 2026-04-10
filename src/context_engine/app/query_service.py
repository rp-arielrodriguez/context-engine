from __future__ import annotations

from pathlib import Path

from ..adapters.scip.cache import load_or_build_store
from ..adapters.scip.exporter import export_ndjson
from ..index_store import IndexStore


def load_store(index_path: Path, force_export: bool = False) -> IndexStore:
    ndjson = export_ndjson(index_path, force=force_export)
    return load_or_build_store(ndjson, IndexStore.from_ndjson, force=force_export)
