# Fixtures

For the semantic edge contract itself, see `docs/semantic-contracts.md`.

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
- Spring detects `shoppingCartService` as an explicitly ambiguous injection with these candidates:
  - `clientShoppingCartService`
  - `repositoryShoppingCartService`
  - `dummyShoppingCartService`
- Reactor publisher type is `Mono`
- Reactor operator chain is exactly `fromFuture -> map`
- Netty runtime boundary is detected

### `raf-loans-reactive`

- controller document and method symbol are present
- endpoint mapping is resolved
- Spring resolves `requestInfoService` to `requestInfoServiceImpl`
- Spring resolves `authorizationService` to `authorizationService`
- Reactor publisher type is `Mono`
- Reactor operator chain is exactly `justOrEmpty -> map -> defaultIfEmpty`
- Netty runtime boundary is detected

### `paymentlink-reactive-service`

- service document and method symbol are present
- Spring resolves at least these field injections:
  - `paymentLinkService` -> `paymentLinkService`
  - `catalogShoppingCartService` -> `catalogShoppingCartServiceImpl`
  - `bannerService` -> `clientBannerService`
- Reactor publisher type is `Mono`
- Reactor operator chain is exactly `fromCallable -> doOnError -> onErrorMap`

### `token-login-legacy`

- legacy document presence check only
- currently treated as a placeholder baseline fixture
