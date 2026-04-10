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

- initialize after startup: roughly 10 to 11 seconds
- `tools/list`: near-instant
- `get_mixed_flow`: near-instant

Recent profile dimensions captured locally:

- SCIP export/cache reuse time
- store load/build time
- representative semantic query time

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
