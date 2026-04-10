# Context Engine Migration Map

## Purpose

This document maps the original local prototype under `~/.config/semantic-layer/inventories/context-engine-phase1/` into this repo.

It is the execution handoff for completing the remaining migration from prototype layout to product layout.

## Locked Decisions

- Repo name: `context-engine`
- Python package: `context_engine`
- Python is the first delivery/runtime language, not the architectural center
- Docs/specs move into the repo from the first migration
- Runtime data must move out of source tree assumptions
- `core/` must remain language-agnostic in design

## Current Migration State

Already migrated into this repo:

- `pyproject.toml`
- installed entrypoints: `context-engine`, `context-engine-mcp`
- root package `src/context_engine/`
- `core/models.py`
- `adapters/runtime/paths.py`
- `adapters/scip/exporter.py`
- `adapters/scip/cache.py`
- `app/query_service.py`
- compatibility re-export shims kept at `model.py`, `config.py`, `exporter.py`, and `query_service.py`
- transitional `index_store.py` still present at package root
- CLI and MCP surfaces under `src/context_engine/surfaces/`
- runtime cache/config defaults moved to `~/.cache/context-engine/` and `~/.config/context-engine/`

Still pending:

- split `index_store.py` across `core/`, `app/`, and semantic adapters
- add dedicated tests in `tests/`
- optionally split docs into fixture/performance focused pages

## Target Repo Layout

```text
context-engine/
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture.md
│   ├── phase1-spec.md
│   ├── migration-map.md
│   ├── fixtures.md
│   └── performance.md
├── tests/
├── scripts/
│   └── measure-mcp.sh
└── src/
    └── context_engine/
        ├── surfaces/
        │   ├── cli/
        │   │   └── main.py
        │   └── mcp/
        │       └── server.py
        ├── app/
        │   ├── query_service.py
        │   ├── fixture_service.py
        │   └── mixed_flow_service.py
        ├── core/
        │   ├── models.py
        │   ├── edge_types.py
        │   ├── provenance.py
        │   ├── query_api.py
        │   ├── fixture_api.py
        │   └── serialization_contracts.py
        ├── adapters/
        │   ├── scip/
        │   │   ├── exporter.py
        │   │   ├── loader.py
        │   │   └── cache.py
        │   ├── semantics/
        │   │   ├── spring.py
        │   │   ├── reactor.py
        │   │   └── netty.py
        │   └── runtime/
        │       ├── paths.py
        │       └── config.py
        └── compat/
            └── schema_versions.py
```

## Runtime Paths

These are not part of the repo and must not be hardcoded into semantic logic:

- Config: `~/.config/context-engine/`
- Cache: `~/.cache/context-engine/`

## File Mapping

## Prototype docs -> repo docs

| Current path | Future path |
|---|---|
| `~/.config/semantic-layer/references/context-engine-phase1-spec.md` | `context-engine/docs/phase1-spec.md` |
| `~/.config/semantic-layer/references/context-engine-migration-map.md` | `context-engine/docs/migration-map.md` |
| `~/.config/semantic-layer/references/context-engine-architecture-boundaries.md` | `context-engine/docs/architecture.md` |
| `~/.config/semantic-layer/inventories/context-engine-phase1/README.md` | `context-engine/README.md` or split into `docs/fixtures.md` + `docs/performance.md` |

Recommended split:
- high-level usage goes to root `README.md`
- fixture definitions go to `docs/fixtures.md`
- performance notes go to `docs/performance.md`

## Prototype code -> repo code

| Current path | Future path |
|---|---|
| `.../src/context_engine_phase1/__init__.py` | `src/context_engine/__init__.py` |
| `.../src/context_engine_phase1/model.py` | `src/context_engine/core/models.py` |
| `.../src/context_engine_phase1/index_store.py` | split across `src/context_engine/adapters/scip/loader.py`, `src/context_engine/adapters/semantics/spring.py`, `src/context_engine/adapters/semantics/reactor.py`, `src/context_engine/adapters/semantics/netty.py`, and `src/context_engine/app/*` |
| `.../src/context_engine_phase1/exporter.py` | `src/context_engine/adapters/scip/exporter.py` |
| `.../src/context_engine_phase1/query_service.py` | `src/context_engine/app/query_service.py` |
| `.../src/context_engine_phase1/cli.py` | `src/context_engine/surfaces/cli/main.py` |
| `.../src/context_engine_phase1/mcp_server.py` | `src/context_engine/surfaces/mcp/server.py` |
| `.../src/context_engine_phase1/config.py` | split into `src/context_engine/adapters/runtime/paths.py` and `src/context_engine/adapters/runtime/config.py` |

## Prototype tools/scripts -> repo scripts

| Current path | Future path |
|---|---|
| `.../tools/ScipJsonExporter.java` | `src/context_engine/adapters/scip/ScipJsonExporter.java` |
| `.../run-cli.sh` | replace with installed entrypoint `context-engine` |
| `.../run-mcp.sh` | replace with installed entrypoint `context-engine-mcp` |
| `.../measure-mcp.sh` | `scripts/measure-mcp.sh` |

## Cache/data handling changes

These prototype assumptions must be removed during migration:

1. Absolute root path assumptions in config
2. Prototype-specific cache directory names
3. Any source-tree-relative runtime path assumptions inside app/core logic

These belong in runtime adapters only.

## Required Refactors During Migration

## 1. Split `index_store.py`

This is the biggest migration task.

Current file responsibilities mixed together:
- raw SCIP data loading
- raw query execution
- Spring extraction
- Reactor extraction
- Netty extraction
- fixture validation
- mixed-flow assembly

Target split:

- `core/models.py`
  - graph/node/edge models
- `core/edge_types.py`
  - edge names/constants
- `core/provenance.py`
  - provenance constants/types
- `core/query_api.py`
  - abstract query contracts
- `core/fixture_api.py`
  - fixture validation contracts

- `adapters/scip/loader.py`
  - NDJSON -> in-memory model
  - raw indexes
- `adapters/scip/cache.py`
  - serialized cache handling
- `adapters/semantics/spring.py`
  - Spring edge extraction
- `adapters/semantics/reactor.py`
  - Reactor edge extraction
- `adapters/semantics/netty.py`
  - Netty edge extraction

- `app/query_service.py`
  - orchestrates loading + queries
- `app/fixture_service.py`
  - fixture validation
- `app/mixed_flow_service.py`
  - mixed-flow assembly

## 2. Replace shell wrappers with package entrypoints

Current:
- `run-cli.sh`
- `run-mcp.sh`

Target:
- `context-engine`
- `context-engine-mcp`

These should be installed via `uv`/`pipx`.

## 3. Separate repo docs from runtime docs

The repo owns:
- architecture
- usage
- fixtures
- performance notes

Runtime state remains outside repo.

## 4. Preserve public behavior during migration

The following behaviors should remain intact after migration:

- `find_symbols`
- `get_symbol`
- `get_references`
- `get_semantic_edges`
- `get_mixed_flow`
- `validate_fixture`
- MCP stdio server behavior for `initialize`, `tools/list`, `tools/call`, `ping`

## Migration Acceptance Criteria

Migration is complete when all are true:

1. Source code no longer lives in `~/.config/semantic-layer/...`
2. Runtime config/cache are externalized to `~/.config/context-engine/` and `~/.cache/context-engine/`
3. CLI entrypoint works as `context-engine`
4. MCP entrypoint works as `context-engine-mcp`
5. Existing fixtures still pass:
   - `shoppingcart-http-main`
   - `raf-loans-reactive`
   - `paymentlink-reactive-service`
   - `token-login-legacy`
6. Existing MCP tools still work
7. Startup measurement still exists and is runnable from repo scripts

## Recommended Execution Order

1. Create repo skeleton
2. Move docs into `docs/`
3. Move simple modules first (`exporter.py`, `query_service.py`, `cli.py`, `mcp_server.py`)
4. Keep `index_store.py` transitional first, then split it
5. Reconnect fixtures and MCP tools
6. Re-run startup measurement and fixture validation
