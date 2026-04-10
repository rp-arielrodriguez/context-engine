# Context Engine Architecture Boundaries

## Purpose

This document defines the architectural boundaries for `context-engine` so the first Python implementation does not become the permanent architecture by accident.

The key rule is:

> Python is the first delivery/runtime language, not the architectural center.

## Layer Overview

The repo is organized into these layers:

- `core/`
- `adapters/`
- `app/`
- `surfaces/`
- `compat/`

## `core/` — language-agnostic contracts

This layer defines stable concepts and must be designed as if it could later be reimplemented in another language.

Allowed in `core/`:
- graph/node/edge models
- edge type definitions
- provenance definitions
- query contracts/interfaces
- fixture validation contracts
- serialization contracts

Not allowed in `core/`:
- file IO
- CLI code
- MCP protocol code
- Python-specific runtime path logic
- SCIP parsing details
- Spring/Reactor/Netty extraction implementation details

The `core/` layer should not know:
- where data is stored
- how it was parsed
- how it is transported to users/agents

## `adapters/` — implementation-specific edges to the outside world

This layer owns integration with concrete technologies.

Allowed in `adapters/`:
- SCIP exporter/loading
- cache persistence
- runtime path/config resolution
- Spring extraction logic
- Reactor extraction logic
- Netty extraction logic

Not allowed in `adapters/`:
- CLI command parsing
- MCP protocol handling
- product-facing workflow orchestration

Adapters may depend on `core/`.
`core/` must never depend on `adapters/`.

## `app/` — orchestration and use-case assembly

This layer coordinates `core/` + `adapters/` into product behaviors.

Allowed in `app/`:
- query service orchestration
- fixture validation orchestration
- mixed-flow assembly
- performance-sensitive loading strategy selection

Not allowed in `app/`:
- transport/protocol code for CLI/MCP
- direct user-facing argument parsing

`app/` is where the main use cases should live.

## `surfaces/` — external interfaces only

This layer exposes the product to humans/agents.

Allowed in `surfaces/`:
- CLI command parsing and output
- MCP stdio protocol handling
- request/response translation

Not allowed in `surfaces/`:
- semantic extraction logic
- graph-building logic
- cache path policy
- business logic for mixed flow / fixture reasoning

Surfaces call into `app/`.
They should stay thin.

## `compat/` — compatibility and versioning only

This layer exists for schema/tool compatibility details.

Allowed in `compat/`:
- schema version constants
- migration markers
- backward-compatible format handling if ever needed

Not allowed in `compat/`:
- semantic extraction logic
- user-facing orchestration

## Dependency Direction

Allowed dependency direction:

```text
surfaces -> app -> core
surfaces -> app -> adapters -> core
app -> adapters -> core
compat -> core
```

Forbidden dependency direction:

```text
core -> adapters
core -> app
core -> surfaces
adapters -> surfaces
app -> surfaces
```

## Stable Boundaries To Preserve

The following boundaries must stay stable even if implementation language changes later:

1. Graph/node/edge model
2. Provenance semantics
3. Query contracts
4. Fixture validation contract
5. Mixed-flow result shape
6. MCP tool behavior

This allows a future architecture like:

- Python CLI/MCP shell
- Java or Zig/Rust/Go graph builder
- shared serialized graph contract

without breaking users.

## Runtime Boundary

Runtime state does not belong in source layers.

Use:
- `~/.config/context-engine/` for config
- `~/.cache/context-engine/` for generated caches/indexes

Only runtime adapters may know these paths.

## Performance Boundary

Performance work should prefer optimizing:
- `adapters/scip`
- `app`

Avoid forcing performance-specific compromises into `core/` unless the contract itself must change.

Current performance fact:
- startup is expensive
- steady-state MCP calls are fast

That implies:
- optimize load path and cache format first
- do not distort query contracts prematurely

## Migration Rule For Existing Prototype

During migration from the prototype:

- if a function mixes multiple layers, split it rather than copying the entanglement forward
- prefer more files with clean ownership over one giant migrated file
- preserve behavior first, then simplify internals

## Review Checklist

When adding new code, ask:

1. Is this a stable concept or a concrete implementation detail?
2. If the core moved out of Python later, would this file still belong here?
3. Is this transport logic, orchestration, or semantic extraction?
4. Does this introduce a forbidden dependency direction?

If those answers are unclear, the boundary is probably wrong.
