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

    fixture = store.validate_fixture("shoppingcart-http-main")
    assert fixture["pass"] is True

    flow = store.get_mixed_flow(
        "semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#getShoppingCart()."
    )
    assert flow["entrypoint"]["http_mappings"]
    assert flow["reactor"]["returns_publisher"]
