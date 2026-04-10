# Performance

## Current Baseline

The main cost in the current prototype is startup and store loading.

Observed behavior:

- CLI calls are relatively slow because each process reloads the semantic store
- long-lived MCP server startup is measurable
- steady-state MCP tool calls are effectively near-instant once the server is warm

## Measurement

Run the local measurement script:

```bash
./scripts/measure-mcp.sh
```

Recent measured behavior in local validation:

- initialize after startup: roughly 10 to 11 seconds
- `tools/list`: near-instant
- `get_mixed_flow`: near-instant

## Optimization Priority

Optimize in this order:

1. exporter/load path
2. cache format and reuse
3. long-lived MCP runtime behavior

Do not distort the semantic query contract just to optimize CLI cold start.
