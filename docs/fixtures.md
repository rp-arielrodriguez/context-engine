# Fixtures

The current semantic acceptance fixtures are:

- `shoppingcart-http-main`
- `raf-loans-reactive`
- `paymentlink-reactive-service`
- `token-login-legacy`

## Purpose

Fixtures act as stable semantic validation scenarios. They are intended to catch regressions in:

- raw SCIP graph loading
- Spring semantic extraction
- Reactor/WebFlux semantic extraction
- Netty runtime-boundary extraction
- mixed-flow assembly

## Current Expectations

### `shoppingcart-http-main`

- controller document is present
- endpoint mapping is resolved
- Spring dependencies and injections are resolved
- Reactor publisher and operator chain are detected
- Netty runtime boundary is detected

### `raf-loans-reactive`

- controller document and method symbol are present
- endpoint mapping is resolved
- Spring dependencies and injections are resolved
- Reactor `justOrEmpty`, `map`, and `defaultIfEmpty` are detected
- Netty runtime boundary is detected

### `paymentlink-reactive-service`

- service document and method symbol are present
- Spring component and dependency edges are resolved
- Reactor `fromCallable`, `doOnError`, and `onErrorMap` are detected

### `token-login-legacy`

- legacy document presence check only
- currently treated as a placeholder baseline fixture
