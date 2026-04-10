#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

python3 - <<'PY'
import json
import os
import subprocess
import time

cmd = [
    'python3',
    '-m',
    'context_engine.surfaces.mcp.server',
    '--index',
    '/Users/ariel.rodriguez/recarga/repos/recarga-ts/index.scip',
]

start = time.time()
proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=os.environ.copy(),
)

def send(msg):
    t0 = time.time()
    proc.stdin.write(json.dumps(msg) + '\n')
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        stderr = proc.stderr.read()
        raise RuntimeError(f"MCP server exited before response. stderr={stderr!r}")
    return time.time() - t0, json.loads(line)

init_dt, _ = send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}})
list_dt, _ = send({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
flow_dt, _ = send({
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
        "name":"get_mixed_flow",
        "arguments":{
            "method_symbol":"semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#getShoppingCart()."
        }
    }
})

print(f"startup_to_initialize: {init_dt:.3f}s")
print(f"tools_list: {list_dt:.3f}s")
print(f"get_mixed_flow: {flow_dt:.3f}s")

proc.terminate()
proc.wait(timeout=5)
PY
