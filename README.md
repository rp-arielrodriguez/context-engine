# Context Engine

Local-first semantic code intelligence backed by SCIP with Spring, Reactor, and Netty semantic layers.

Status: early alpha.

- SCIP index export pipeline (binary `.scip` -> NDJSON)
- In-memory semantic model
- Initial query endpoints

## Implemented Queries

- `find_documents`
- `find_symbols`
- `get_symbol`
- `get_occurrences`
- `get_references`
- `trace_semantic_path` (raw call graph from SCIP occurrences)
- `get_semantic_edges` (Spring, Reactor, and Netty Tier 1 derived edges)
- `get_mixed_flow` (HTTP handler -> Spring -> Reactor -> Netty)
- `validate_fixture` (`shoppingcart-http-main`, `raf-loans-reactive`, `paymentlink-reactive-service`, `token-login-legacy`)

## Usage

Preferred local setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

After that, the repo provides these shell commands from the activated venv:

- `context-engine`
- `context-engine-mcp`

Install test dependencies too:

```bash
python -m pip install -e '.[dev]'
```

## CLI Usage

```bash
context-engine \
  --index "/path/to/index.scip" \
  find-symbols --query "ShoppingCartController"
```

Get symbol details:

```bash
context-engine \
  --index "/path/to/index.scip" \
  get-symbol --symbol "semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#"
```

Validate baseline fixture:

```bash
context-engine \
  --index "/path/to/index.scip" \
  validate-fixture --fixture-id "shoppingcart-http-main"
```

Other available fixtures:

- `raf-loans-reactive`
- `paymentlink-reactive-service`
- `token-login-legacy`

Get a mixed semantic flow from an HTTP handler method:

```bash
context-engine \
  --index "/path/to/index.scip" \
  get-mixed-flow --method-symbol "semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#getShoppingCart()."
```

## MCP Server

Run the minimal stdio MCP server:

```bash
context-engine-mcp \
  --index "/path/to/index.scip"
```

Initial MCP tools:

- `find_documents`
- `find_symbols`
- `get_symbol`
- `get_references`
- `get_semantic_edges`
- `get_mixed_flow`
- `validate_fixture`

No-install fallback:

If you do not want to create a local venv, you can run directly from source with `PYTHONPATH`:

```bash
PYTHONPATH="src" \
python3 -m context_engine.surfaces.mcp.server \
  --index "/path/to/index.scip"
```

The same pattern works for the CLI:

```bash
PYTHONPATH="src" \
python3 -m context_engine.surfaces.cli.main \
  --index "/path/to/index.scip" \
  validate-fixture --fixture-id "shoppingcart-http-main"
```

## Performance Notes

- Repeated CLI commands are still relatively slow because each new process must load the cached semantic store.
- The long-lived MCP server is much faster after startup.
- On the current implementation, startup is the main cost; individual tool calls are effectively near-instant once the server is running.

Measure it locally:

```bash
./scripts/measure-mcp.sh
```

## Notes

- This project uses a tiny Java exporter to parse SCIP protobuf safely using the official `scip-java-proto` classes.
- Export output is cached under `~/.cache/context-engine/`.
- Runtime config belongs under `~/.config/context-engine/`.
- No repository files are modified during query runs.
- Spring Tier 1 currently resolves bean candidates from `@Service`/controller stereotypes, implemented interfaces, and `@Bean` factory methods, and emits both class-level `spring.depends_on` and direct field-site `spring.injects` edges.
- Reactor Tier 1 currently models return publishers and operator chains; Netty Tier 1 currently models reactive HTTP runtime boundaries heuristically.

## Project Docs

- architecture boundaries: `docs/architecture.md`
- phase 1 scope: `docs/phase1-spec.md`
- fixtures: `docs/fixtures.md`
- performance notes: `docs/performance.md`
- migration status: `docs/migration-map.md`

## GitHub

Intended repository URL:

- `https://github.com/rp-arielrodriguez/context-engine`

## Contributing

- contribution guide: `CONTRIBUTING.md`
- code of conduct: `CODE_OF_CONDUCT.md`
- security policy: `SECURITY.md`

## License

Apache-2.0. See `LICENSE`.
