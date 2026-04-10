#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INDEX_PATH="${1:-}"

if [[ -z "$INDEX_PATH" ]]; then
  printf 'Usage: %s /path/to/index.scip\n' "$0" >&2
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

python3 - <<'PY' "$INDEX_PATH"
import json
import sys
import time
from pathlib import Path

from context_engine.adapters.scip.exporter import export_ndjson
from context_engine.adapters.scip.cache import load_or_build_store
from context_engine.index_store import IndexStore

index_path = Path(sys.argv[1])

start = time.time()
ndjson = export_ndjson(index_path)
export_dt = time.time() - start

start = time.time()
store = load_or_build_store(ndjson, IndexStore.from_ndjson, force=False)
load_dt = time.time() - start

start = time.time()
store.get_mixed_flow(
    "semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#getShoppingCart()."
)
query_dt = time.time() - start

print(json.dumps({
    "index": str(index_path),
    "ndjson": str(ndjson),
    "export_seconds": round(export_dt, 3),
    "store_load_seconds": round(load_dt, 3),
    "sample_query_seconds": round(query_dt, 3),
}, indent=2))
PY
