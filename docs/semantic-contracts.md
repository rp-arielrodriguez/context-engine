# Semantic Contracts

This document describes the semantic edges and fixtures currently supported by Context Engine.

The current implementation mixes raw SCIP facts with framework-aware derived edges.

## Stability

- raw SCIP-backed queries are the strongest contract in the project today
- Spring, Reactor, and Netty semantic edges are derived contracts
- some derived edges are heuristic and should be treated as alpha-level behavior

## Raw Queries

These are backed directly by loaded SCIP data and in-memory indexes:

- `find_documents`
- `find_symbols`
- `get_symbol`
- `get_occurrences`
- `get_references`
- `trace_semantic_path`

## Derived Semantic Edges

### Spring

Provenance: `spring-derived`

Current edge types:

- `spring.component_declares`
- `spring.bean_factory_produces`
- `spring.endpoint_maps_to`
- `spring.depends_on`
- `spring.injects`

Current basis:

- stereotype annotations such as `@Service`, `@Component`, `@Controller`, `@RestController`
- request mapping annotations
- constructor and final-field inference
- `@Bean` factory methods
- imported type matching for candidate bean resolution

Heuristic areas:

- bean candidate disambiguation when multiple candidates share the same type
- field and constructor inference in complex source layouts

### Reactor

Provenance: `reactor-derived`

Current edge types:

- `reactor.returns_publisher`
- `reactor.http_handler_starts`
- `reactor.operator_applies`
- `reactor.flows_to`
- `reactor.error_fallback_to`

Current operator coverage includes:

- `fromFuture`
- `fromCallable`
- `map`
- `flatMap`
- `filter`
- `zip`
- `defaultIfEmpty`
- `doOnError`
- `onErrorResume`
- `onErrorMap`
- `just`
- `justOrEmpty`

Heuristic areas:

- operator chain interpretation is symbol-driven rather than full dataflow modeling
- stage graph currently focuses on a practical subset of Reactor behavior

### Netty

Provenance: `netty-derived`

Current edge types:

- `netty.runtime_boundary`

Current basis:

- reactive HTTP entrypoints with detected Reactor return stages

Heuristic areas:

- no deep channel pipeline or handler graph modeling yet
- runtime boundary inference is intentionally shallow today

## Mixed Flow Contract

`get_mixed_flow(method_symbol)` returns a structured view over:

- HTTP entrypoint mapping
- Spring component and dependency context
- Reactor return stage and operator chain
- Netty runtime boundary

It is intended as an application-facing composition of lower-level contracts, not as the source of truth itself.

## Fixture Contracts

Current fixture IDs:

- `shoppingcart-http-main`
- `raf-loans-reactive`
- `paymentlink-reactive-service`
- `token-login-legacy`

Fixture purpose:

- protect semantic extraction from regressions
- give named acceptance scenarios across different framework patterns

Current fixture validation status:

- all fixture IDs are covered by the env-gated real-index integration suite when `CONTEXT_ENGINE_TEST_INDEX` is set

## Recommended Interpretation

- treat raw SCIP lookups as the strongest baseline
- treat derived semantic edges as useful but still evolving contracts
- use fixtures to understand intended current behavior
