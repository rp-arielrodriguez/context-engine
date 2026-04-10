from __future__ import annotations

import hashlib
import os
import pickle
from pathlib import Path
from typing import Callable, TypeVar

from ..runtime.paths import STORE_CACHE_DIR


T = TypeVar("T")
STORE_CACHE_VERSION = 5


def _store_cache_file(ndjson_path: Path) -> Path:
    stat = ndjson_path.stat()
    fingerprint = f"v{STORE_CACHE_VERSION}::{ndjson_path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}".encode("utf-8")
    digest = hashlib.sha256(fingerprint).hexdigest()[:16]
    STORE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return STORE_CACHE_DIR / f"store-{digest}.pickle"


def load_or_build_store(ndjson_path: Path, builder: Callable[[Path], T], force: bool = False) -> T:
    cache_file = _store_cache_file(ndjson_path)

    if cache_file.exists() and not force:
        with cache_file.open("rb") as fh:
            return pickle.load(fh)

    store = builder(ndjson_path)
    tmp_file = cache_file.with_suffix(cache_file.suffix + f".{os.getpid()}.tmp")
    with tmp_file.open("wb") as fh:
        pickle.dump(store, fh, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_file.replace(cache_file)
    return store
