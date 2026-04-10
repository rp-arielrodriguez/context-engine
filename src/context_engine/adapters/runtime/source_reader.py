from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse


def project_root_path(project_root: str) -> Path | None:
    root = project_root or ""
    if not root:
        return None
    if root.startswith("file://"):
        parsed = urlparse(root)
        return Path(unquote(parsed.path))
    return Path(root)


def read_source(store, document: str) -> str:
    if document in store._source_cache:
        return store._source_cache[document]
    root = project_root_path(store.metadata.project_root)
    if root is None:
        store._source_cache[document] = ""
        return ""
    path = root / document
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        text = ""
    store._source_cache[document] = text
    return text
