from __future__ import annotations

import os
from pathlib import Path

import pytest

from context_engine.app.query_service import load_store


REAL_INDEX_ENV = "CONTEXT_ENGINE_TEST_INDEX"


@pytest.mark.skipif(not os.environ.get(REAL_INDEX_ENV), reason="real index not configured")
def test_real_index_fixture_and_flow_smoke() -> None:
    index_path = Path(os.environ[REAL_INDEX_ENV])
    store = load_store(index_path)

    for fixture_id in [
        "shoppingcart-http-main",
        "raf-loans-reactive",
        "paymentlink-reactive-service",
        "token-login-legacy",
    ]:
        fixture = store.validate_fixture(fixture_id)
        assert fixture["pass"] is True, fixture_id
        assert fixture["checks"]
        assert all(isinstance(value, bool) for value in fixture["checks"].values())

    flow = store.get_mixed_flow(
        "semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#getShoppingCart()."
    )
    assert flow["entrypoint"]["http_mappings"]
    assert flow["reactor"]["returns_publisher"]
    assert "Mono" in flow["reactor"]["publisher_types"]
    assert flow["spring"]["depends_on"]
    assert flow["netty"]["runtime_boundaries"]
    assert all(stage["flow_kind"] in {"reactor.operator_applies", "reactor.flows_to", "reactor.error_fallback_to"} for stage in flow["reactor"]["operator_chain"])


@pytest.mark.skipif(not os.environ.get(REAL_INDEX_ENV), reason="real index not configured")
def test_real_index_secondary_reactive_flow_smoke() -> None:
    index_path = Path(os.environ[REAL_INDEX_ENV])
    store = load_store(index_path)

    flow = store.get_mixed_flow(
        "semanticdb maven . . com/recargapay/bff/app/raf/server/controller/BffLoansAuthorizationsController#getLandingPage()."
    )

    assert flow["entrypoint"]["http_mappings"]
    assert flow["reactor"]["operator_chain"]
    operators = [stage["operator"] for stage in flow["reactor"]["operator_chain"]]
    flow_kinds = [stage["flow_kind"] for stage in flow["reactor"]["operator_chain"]]
    assert "map" in operators
    assert "reactor.operator_applies" in flow_kinds


@pytest.mark.skipif(not os.environ.get(REAL_INDEX_ENV), reason="real index not configured")
def test_real_index_paymentlink_reactive_semantics() -> None:
    index_path = Path(os.environ[REAL_INDEX_ENV])
    store = load_store(index_path)

    fixture = store.validate_fixture("paymentlink-reactive-service")
    assert fixture["pass"] is True
    assert fixture["checks"]["reactor_from_callable"] is True
    assert fixture["checks"]["reactor_do_on_error"] is True
    assert fixture["checks"]["reactor_on_error_map"] is True
