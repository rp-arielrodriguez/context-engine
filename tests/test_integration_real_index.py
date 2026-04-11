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
    assert flow["reactor"]["publisher_types"] == ["Mono"]
    assert flow["spring"]["depends_on"]
    assert flow["netty"]["runtime_boundaries"]
    assert all(stage["flow_kind"] in {"reactor.operator_applies", "reactor.flows_to", "reactor.error_fallback_to"} for stage in flow["reactor"]["operator_chain"])

    shopping_cart_injections = [
        field
        for field in flow["spring"]["field_injections"]
        if field["field"]["display_name"] == "shoppingCartService"
    ]
    assert len(shopping_cart_injections) == 1
    shopping_cart_resolution = shopping_cart_injections[0]["resolution"]
    assert shopping_cart_resolution["match_state"] == "ambiguous"
    assert shopping_cart_resolution["candidate_count"] == 3
    assert sorted(shopping_cart_resolution["candidate_bean_names"]) == [
        "clientShoppingCartService",
        "dummyShoppingCartService",
        "repositoryShoppingCartService",
    ]

    shopping_cart_operators = [stage["operator"] for stage in flow["reactor"]["operator_chain"]]
    assert shopping_cart_operators == ["fromFuture", "map"]


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
    assert flow["reactor"]["publisher_types"] == ["Mono"]
    assert operators == ["justOrEmpty", "map", "defaultIfEmpty"]
    assert "reactor.operator_applies" in flow_kinds

    request_info_injections = [
        field
        for field in flow["spring"]["field_injections"]
        if field["field"]["display_name"] == "requestInfoService"
    ]
    assert len(request_info_injections) == 1
    resolution = request_info_injections[0]["resolution"]
    assert resolution["match_state"] == "resolved"
    assert resolution["candidate_count"] == 1
    bean_names = resolution["candidate_bean_names"]
    assert bean_names == ["requestInfoServiceImpl"]


@pytest.mark.skipif(not os.environ.get(REAL_INDEX_ENV), reason="real index not configured")
def test_real_index_paymentlink_reactive_semantics() -> None:
    index_path = Path(os.environ[REAL_INDEX_ENV])
    store = load_store(index_path)

    fixture = store.validate_fixture("paymentlink-reactive-service")
    assert fixture["pass"] is True
    assert fixture["checks"]["spring_payment_link_service_resolved"] is True
    assert fixture["checks"]["spring_catalog_shopping_cart_service_resolved"] is True
    assert fixture["checks"]["spring_banner_service_resolved"] is True
    assert fixture["checks"]["reactor_from_callable"] is True
    assert fixture["checks"]["reactor_do_on_error"] is True
    assert fixture["checks"]["reactor_on_error_map"] is True
    assert fixture["checks"]["reactor_operator_sequence"] is True

    flow = store.get_mixed_flow(
        "semanticdb maven . . com/recargapay/bff/app/paymentlink/server/service/BffPaymentLinkServiceImpl#createPaymentLinkFromPaymentApi()."
    )
    assert flow["reactor"]["publisher_types"] == ["Mono"]
    assert [stage["operator"] for stage in flow["reactor"]["operator_chain"]] == [
        "fromCallable",
        "doOnError",
        "onErrorMap",
    ]

    paymentlink_fields = {
        field["field"]["display_name"]: field["resolution"]
        for field in flow["spring"]["field_injections"]
    }
    assert paymentlink_fields["paymentLinkService"] == {
        "match_state": "resolved",
        "candidate_count": 1,
        "candidate_bean_names": ["paymentLinkService"],
    }
    assert paymentlink_fields["catalogShoppingCartService"] == {
        "match_state": "resolved",
        "candidate_count": 1,
        "candidate_bean_names": ["catalogShoppingCartServiceImpl"],
    }
    assert paymentlink_fields["bannerService"] == {
        "match_state": "resolved",
        "candidate_count": 1,
        "candidate_bean_names": ["clientBannerService"],
    }
