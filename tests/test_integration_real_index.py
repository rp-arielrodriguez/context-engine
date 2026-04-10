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
    assert flow["spring"]["depends_on"]
    assert flow["netty"]["runtime_boundaries"]


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
    assert "map" in operators
