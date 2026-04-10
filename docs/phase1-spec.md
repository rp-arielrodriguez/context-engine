# Context Engine Phase 1 Spec

## Objective

Build the first usable local semantic engine on top of `index.scip` with equal first-class support for:

- Spring semantics
- Reactor/WebFlux semantics
- Netty semantics

Phase 1 must support manual validation (CLI) and agent consumption (MCP) on the same semantic core.

## Locked Validation Fixtures

### Primary HTTP-first anchor

- `src/com/recargapay/shoppingcart/controllers/ShoppingCartController.java`
- Method: `getShoppingCart(...)`

### Secondary reactive Spring endpoint

- `src/com/recargapay/bff/app/raf/server/controller/BffLoansAuthorizationsController.java`
- Methods:
  - `getLandingPage()`
  - `getLoanAuthorizationsByUuid(...)`

### Reactive service target

- `src/com/recargapay/bff/app/paymentlink/server/service/BffPaymentLinkServiceImpl.java`
- Methods:
  - `create(...)`
  - `createPaymentLinkFromPaymentApi(...)`

### Legacy comparison target (non-anchor)

- `src/com/si/cloncom/ts/rest/api/TokenEndpoint.java`
- Method: `login()`

## Graph Model

## Node shape

```json
{
  "id": "string",
  "kind": "document|symbol|http_entrypoint|spring_bean|reactive_stage|netty_component",
  "name": "string",
  "symbol": "string|null",
  "path": "string|null",
  "metadata": {"key": "value"}
}
```

## Edge shape

```json
{
  "id": "string",
  "source": "node_id",
  "target": "node_id",
  "type": "edge_type",
  "provenance": "raw-scip|spring-derived|reactor-derived|netty-derived",
  "confidence": 1.0,
  "metadata": {"key": "value"}
}
```

Notes:

- `confidence` for Phase 1 defaults to `1.0` unless inference is heuristic.
- `metadata` must include source hints (for example file path, method, annotation, operator).

## Edge Types (Tier 1)

## Raw SCIP edges (`raw-scip`)

- `raw.defines` document -> symbol
- `raw.references` symbol -> symbol
- `raw.occurs_in` symbol -> document
- `raw.calls` caller symbol -> callee symbol
- `raw.imports` document -> document_or_symbol
- `raw.encloses` symbol -> symbol

`raw.calls` may be inferred from occurrence/use patterns when explicit call relationship is unavailable in a single step.

## Spring edges (`spring-derived`)

- `spring.component_declares` class_symbol -> spring_bean
- `spring.bean_factory_produces` factory_method_symbol -> spring_bean
- `spring.injects` injection_site_symbol -> spring_bean
- `spring.qualifier_selects` qualifier_symbol -> spring_bean
- `spring.depends_on` spring_bean -> spring_bean
- `spring.endpoint_maps_to` http_entrypoint -> class_or_method_symbol

Scope for Tier 1 annotations:

- `@Service`
- `@Component`
- `@Bean`
- `@Autowired`
- `@Inject`
- `@Qualifier`

## Reactor/WebFlux edges (`reactor-derived`)

- `reactor.returns_publisher` method_symbol -> reactive_stage
- `reactor.operator_applies` reactive_stage -> reactive_stage
- `reactor.flows_to` reactive_stage -> reactive_stage
- `reactor.error_fallback_to` reactive_stage -> reactive_stage
- `reactor.subscribes_to` method_or_stage -> reactive_stage
- `reactor.http_handler_starts` http_entrypoint -> reactive_stage

Scope for Tier 1 operators:

- `map`
- `flatMap`
- `filter`
- `zip`
- `onErrorResume`

Scope for Tier 1 types:

- `Mono`
- `Flux`

## Netty edges (`netty-derived`)

- `netty.runtime_boundary` reactive_stage_or_http_entrypoint -> netty_component
- `netty.pipeline_contains` netty_component -> netty_component
- `netty.handler_precedes` netty_component -> netty_component
- `netty.inbound_flows_to` netty_component -> netty_component
- `netty.outbound_flows_to` netty_component -> netty_component
- `netty.configures` symbol -> netty_component

Tier 1 Netty requirement:

- Prioritize Reactor Netty integration/runtime boundaries for HTTP-first flow.
- Include direct pipeline/handler edges when explicit code is available.

## Minimal Query API (Phase 1)

All queries are exposed via CLI and MCP over the same semantic core.

## 1) `find_documents`

Input:

- `query` (string)
- `limit` (int, optional)

Output:

- list of documents with path and match metadata

## 2) `find_symbols`

Input:

- `query` (string)
- `path_filter` (string, optional)
- `kind_filter` (string, optional)
- `limit` (int, optional)

Output:

- list of symbols with id, display name, path, enclosing symbol

## 3) `get_document`

Input:

- `path` (string)

Output:

- document node
- symbols declared in document
- outgoing/incoming edges summary

## 4) `get_symbol`

Input:

- `symbol_id` (string)

Output:

- symbol node
- declarations/occurrences
- related edges by provenance

## 5) `get_occurrences`

Input:

- `symbol_id` (string)
- `path_filter` (string, optional)

Output:

- occurrence list with location and role

## 6) `get_references`

Input:

- `symbol_id` (string)
- `path_filter` (string, optional)

Output:

- referencing symbols/documents

## 7) `get_semantic_edges`

Input:

- `node_id` (string)
- `provenance_filter` (array, optional)
- `type_filter` (array, optional)
- `direction` (`out|in|both`, default `both`)

Output:

- edge list with type, provenance, confidence, metadata

## 8) `trace_semantic_path`

Input:

- `start_node_id` (string)
- `max_depth` (int)
- `provenance_filter` (array, optional)
- `type_filter` (array, optional)

Output:

- candidate paths from start node
- each path as ordered nodes + edges

## 9) `validate_fixture`

Input:

- `fixture_id` (`shoppingcart-http-main|raf-loans-reactive|paymentlink-reactive-service|token-login-legacy`)

Output:

- pass/fail per expected edge assertions
- missing edges list

## 10) `get_mixed_flow`

Input:

- `method_symbol` (string)

Output:

- HTTP mapping for the handler method
- Spring component and resolved injection/dependency edges
- Reactor return stage and ordered operator chain
- Netty runtime boundary edges

## Fixture Acceptance Assertions

## `shoppingcart-http-main`

Must find:

- Spring mapping edge for `ShoppingCartController.getShoppingCart(...)`
- Reactor publisher edge from handler method
- at least one Netty runtime boundary edge reachable from handler flow

## `raf-loans-reactive`

Must find:

- endpoint mapping edges for selected methods
- Reactor chain edges (`Mono.justOrEmpty` path acceptable)
- Spring class/service dependency edges involved in method flow

## `paymentlink-reactive-service`

Must find:

- Reactor chain edges involving `create(...)` and `createPaymentLinkFromPaymentApi(...)`
- operator edges including `zip` and `onErrorMap`/fallback mapping
- Spring service declaration/dependency edges

## `token-login-legacy`

Must find:

- endpoint routing linkage for legacy flow
- classify provenance as legacy-compatible path (not primary Phase 1 anchor)

## Model-aware Execution Chunks

## Chunk A — Spec lock

- Owner: `gpt-5.4`
- Deliverable: finalized graph schema + edge types + query API + fixture assertions
- Stop if: multiple incompatible graph designs remain
- Next: `Opus`/`GLM-5.1` if ambiguous, else `Codex`

## Chunk B — Core implementation

- Owner: `Codex`
- Deliverable: SCIP reader + graph core + provenance edges
- Stop if: core cannot represent required edge types cleanly
- Next: `gpt-5.4`

## Chunk C/D/E — Enrichment passes

- Owner: `Codex`
- Deliverable: Spring, Reactor, Netty Tier 1 passes
- Stop if: semantic ambiguity exceeds Tier 1 scope
- Next: `gpt-5.4`

## Chunk F/G — Surfaces

- Owner: `Codex`
- Deliverable: inspector CLI + MCP adapter
- Stop if: query contract gaps appear
- Next: `gpt-5.4`

## Chunk H — Validation loops

- Owner: `Haiku`
- Deliverable: fixture pass/fail matrix
- Stop if: failures are semantic (not mechanical)
- Next: `Codex` or `gpt-5.4`

## Immediate Next Step

Implement Chunk B with a minimal in-memory graph core and the first four raw query endpoints:

- `find_documents`
- `find_symbols`
- `get_symbol`
- `get_occurrences`

Then run `validate_fixture` for `shoppingcart-http-main` as the first gate.

## Minimal MCP Surface (Current Prototype)

The current prototype exposes a dependency-free stdio MCP server with these tools:

- `find_documents`
- `find_symbols`
- `get_symbol`
- `get_references`
- `get_semantic_edges`
- `get_mixed_flow`
- `validate_fixture`
