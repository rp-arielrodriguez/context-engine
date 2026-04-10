# Performance

## Current Baseline

The main cost in the current implementation is startup and store loading.

Observed behavior:

- CLI calls are relatively slow because each process reloads the semantic store
- long-lived MCP server startup is measurable
- steady-state MCP tool calls are effectively near-instant once the server is warm

## Measurement

Run the local measurement script:

```bash
./scripts/measure-mcp.sh /path/to/index.scip
```

For a more explicit startup breakdown, run:

```bash
./scripts/profile-startup.sh /path/to/index.scip
```

Recent measured behavior in local validation:

- previous MCP initialize after startup: roughly 36 seconds on the larger real index used for recent profiling
- current MCP initialize after the latest optimization pass: roughly 30 seconds on the same real index
- `tools/list`: near-instant
- `get_mixed_flow`: near-instant

Recent profile dimensions captured locally:

- SCIP export/cache reuse time
- store load/build time
- representative semantic query time

Most recent local profile snapshot:

- export/cache reuse: ~0.0s
- store load from cache/build path: ~29.8s
- representative semantic query: ~0.02s

Additional local measurements after the latest optimization pass:

- cached `load_or_build_store(...)`: ~6.5s to ~7.5s
- MCP startup-to-initialize: improved from ~36.0s to ~30.4s

## Optimization Priority

Optimize in this order:

1. exporter/load path
2. cache format and reuse
3. long-lived MCP runtime behavior

Do not distort the semantic query contract just to optimize CLI cold start.

## Current Direction

Prefer improvements in this order:

1. reuse cached exports and store state well
2. reduce store build/load overhead
3. keep MCP long-lived so repeated queries avoid cold-start costs

Current biggest opportunity remains store build/load internals rather than exporter work or steady-state query execution.
