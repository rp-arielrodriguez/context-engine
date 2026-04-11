from __future__ import annotations

from .flow_helpers import has_operator


MONO_SYMBOL = "semanticdb maven . . reactor/core/publisher/Mono#"


def _field_resolution_by_name(store, method_symbol: str, field_name: str) -> dict | None:
    flow = store.get_mixed_flow(method_symbol)
    for field in flow["spring"]["field_injections"]:
        if field["field"]["display_name"] == field_name:
            return field["resolution"]
    return None


def _field_resolution_matches(
    store,
    method_symbol: str,
    field_name: str,
    *,
    match_state: str,
    candidate_names: list[str],
) -> bool:
    resolution = _field_resolution_by_name(store, method_symbol, field_name)
    if resolution is None:
        return False
    return (
        resolution.get("match_state") == match_state
        and sorted(resolution.get("candidate_bean_names", [])) == sorted(candidate_names)
    )


def _operator_sequence_matches(store, method_symbol: str, expected: list[str]) -> bool:
    flow = store.get_mixed_flow(method_symbol)
    return [stage["operator"] for stage in flow["reactor"]["operator_chain"]] == expected


def _fixture_context(store, document: str) -> dict:
    cache = getattr(store, "_fixture_context_cache", None)
    if cache is None:
        cache = {}
        store._fixture_context_cache = cache
    if document not in cache:
        cache[document] = {
            "document_present": document in store.documents_by_path,
            "mono_references": [reference for reference in store.references_by_symbol.get(MONO_SYMBOL, []) if reference.document == document],
        }
    return cache[document]


def validate_fixture(store, fixture_id: str) -> dict:
    if fixture_id == "shoppingcart-http-main":
        controller_doc = "src/com/recargapay/shoppingcart/controllers/ShoppingCartController.java"
        method_symbol = (
            "semanticdb maven . . com/recargapay/shoppingcart/controllers/"
            "ShoppingCartController#getShoppingCart()."
        )
        class_symbol = "semanticdb maven . . com/recargapay/shoppingcart/controllers/ShoppingCartController#"
        field_symbol = (
            "semanticdb maven . . com/recargapay/shoppingcart/controllers/"
            "ShoppingCartController#shoppingCartService."
        )
        context = _fixture_context(store, controller_doc)
        has_doc = context["document_present"]
        has_method = method_symbol in store.symbols_by_id
        refs_to_mono = context["mono_references"]
        method_calls_out = sorted(store.calls_out_by_symbol.get(method_symbol, set()))
        return_stage = f"reactorstage:return:{method_symbol}"

        checks = {
            "document_present": has_doc,
            "method_symbol_present": has_method,
            "mono_reference_in_controller": len(refs_to_mono) > 0,
            "method_has_calls_out": len(method_calls_out) > 0,
            "spring_component_declares": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.component_declares"])) > 0,
            "spring_endpoint_maps_to": len(store.get_semantic_edges(method_symbol, direction="in", type_filter=["spring.endpoint_maps_to"])) > 0,
            "spring_depends_on_resolved": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.depends_on"])) > 0,
            "spring_injects_resolved": len(store.get_semantic_edges(field_symbol, direction="out", type_filter=["spring.injects"])) > 0,
            "spring_shoppingcart_service_ambiguous": _field_resolution_matches(
                store,
                method_symbol,
                "shoppingCartService",
                match_state="ambiguous",
                candidate_names=[
                    "clientShoppingCartService",
                    "repositoryShoppingCartService",
                    "dummyShoppingCartService",
                ],
            ),
            "reactor_returns_publisher": len(store.get_semantic_edges(method_symbol, direction="out", type_filter=["reactor.returns_publisher"])) > 0,
            "reactor_operator_chain": len(store.get_semantic_edges(return_stage, direction="out", type_filter=["reactor.operator_applies"])) > 0,
            "reactor_operator_sequence": _operator_sequence_matches(store, method_symbol, ["fromFuture", "map"]),
            "netty_runtime_boundary": len(store.get_semantic_edges(return_stage, direction="out", type_filter=["netty.runtime_boundary"])) > 0,
        }

        return {
            "fixture_id": fixture_id,
            "pass": all(checks.values()),
            "checks": checks,
            "details": {
                "calls_out_count": len(method_calls_out),
                "mono_reference_count": len(refs_to_mono),
                "calls_out_preview": method_calls_out[:10],
            },
        }

    if fixture_id == "raf-loans-reactive":
        controller_doc = "src/com/recargapay/bff/app/raf/server/controller/BffLoansAuthorizationsController.java"
        method_symbol = (
            "semanticdb maven . . com/recargapay/bff/app/raf/server/controller/"
            "BffLoansAuthorizationsController#getLandingPage()."
        )
        class_symbol = (
            "semanticdb maven . . com/recargapay/bff/app/raf/server/controller/"
            "BffLoansAuthorizationsController#"
        )
        field_symbol = (
            "semanticdb maven . . com/recargapay/bff/app/raf/server/controller/"
            "BffLoansAuthorizationsController#requestInfoService."
        )
        return_stage = f"reactorstage:return:{method_symbol}"
        context = _fixture_context(store, controller_doc)
        refs_to_mono = context["mono_references"]

        checks = {
            "document_present": context["document_present"],
            "method_symbol_present": method_symbol in store.symbols_by_id,
            "spring_component_declares": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.component_declares"])) > 0,
            "spring_endpoint_maps_to": len(store.get_semantic_edges(method_symbol, direction="in", type_filter=["spring.endpoint_maps_to"])) > 0,
            "spring_depends_on_resolved": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.depends_on"])) > 0,
            "spring_injects_resolved": len(store.get_semantic_edges(field_symbol, direction="out", type_filter=["spring.injects"])) > 0,
            "spring_request_info_resolved": _field_resolution_matches(
                store,
                method_symbol,
                "requestInfoService",
                match_state="resolved",
                candidate_names=["requestInfoServiceImpl"],
            ),
            "spring_authorization_service_resolved": _field_resolution_matches(
                store,
                method_symbol,
                "authorizationService",
                match_state="resolved",
                candidate_names=["authorizationService"],
            ),
            "mono_reference_in_controller": len(refs_to_mono) > 0,
            "reactor_returns_publisher": len(store.get_semantic_edges(method_symbol, direction="out", type_filter=["reactor.returns_publisher"])) > 0,
            "reactor_just_or_empty": has_operator(store, return_stage, "justOrEmpty"),
            "reactor_map": has_operator(store, return_stage, "map"),
            "reactor_default_if_empty": has_operator(store, return_stage, "defaultIfEmpty"),
            "reactor_operator_sequence": _operator_sequence_matches(store, method_symbol, ["justOrEmpty", "map", "defaultIfEmpty"]),
            "netty_runtime_boundary": len(store.get_semantic_edges(return_stage, direction="out", type_filter=["netty.runtime_boundary"])) > 0,
        }

        return {
            "fixture_id": fixture_id,
            "pass": all(checks.values()),
            "checks": checks,
            "details": {
                "mono_reference_count": len(refs_to_mono),
                "operators_checked": ["justOrEmpty", "map", "defaultIfEmpty"],
            },
        }

    if fixture_id == "paymentlink-reactive-service":
        service_doc = "src/com/recargapay/bff/app/paymentlink/server/service/BffPaymentLinkServiceImpl.java"
        class_symbol = (
            "semanticdb maven . . com/recargapay/bff/app/paymentlink/server/service/"
            "BffPaymentLinkServiceImpl#"
        )
        field_symbol = (
            "semanticdb maven . . com/recargapay/bff/app/paymentlink/server/service/"
            "BffPaymentLinkServiceImpl#paymentLinkService."
        )
        method_symbol = (
            "semanticdb maven . . com/recargapay/bff/app/paymentlink/server/service/"
            "BffPaymentLinkServiceImpl#createPaymentLinkFromPaymentApi()."
        )
        return_stage = f"reactorstage:return:{method_symbol}"
        context = _fixture_context(store, service_doc)
        refs_to_mono = context["mono_references"]

        checks = {
            "document_present": context["document_present"],
            "class_symbol_present": class_symbol in store.symbols_by_id,
            "method_symbol_present": method_symbol in store.symbols_by_id,
            "spring_component_declares": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.component_declares"])) > 0,
            "spring_depends_on_resolved": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.depends_on"])) > 0,
            "spring_injects_resolved": len(store.get_semantic_edges(field_symbol, direction="out", type_filter=["spring.injects"])) > 0,
            "spring_payment_link_service_resolved": _field_resolution_matches(
                store,
                method_symbol,
                "paymentLinkService",
                match_state="resolved",
                candidate_names=["paymentLinkService"],
            ),
            "spring_catalog_shopping_cart_service_resolved": _field_resolution_matches(
                store,
                method_symbol,
                "catalogShoppingCartService",
                match_state="resolved",
                candidate_names=["catalogShoppingCartServiceImpl"],
            ),
            "spring_banner_service_resolved": _field_resolution_matches(
                store,
                method_symbol,
                "bannerService",
                match_state="resolved",
                candidate_names=["clientBannerService"],
            ),
            "mono_reference_in_service": len(refs_to_mono) > 0,
            "reactor_returns_publisher": len(store.get_semantic_edges(method_symbol, direction="out", type_filter=["reactor.returns_publisher"])) > 0,
            "reactor_from_callable": has_operator(store, return_stage, "fromCallable"),
            "reactor_do_on_error": has_operator(store, return_stage, "doOnError"),
            "reactor_on_error_map": has_operator(store, return_stage, "onErrorMap"),
            "reactor_operator_sequence": _operator_sequence_matches(store, method_symbol, ["fromCallable", "doOnError", "onErrorMap"]),
        }

        return {
            "fixture_id": fixture_id,
            "pass": all(checks.values()),
            "checks": checks,
            "details": {
                "mono_reference_count": len(refs_to_mono),
                "operators_checked": ["fromCallable", "doOnError", "onErrorMap"],
            },
        }

    if fixture_id == "token-login-legacy":
        token_doc = "src/com/si/cloncom/ts/rest/api/TokenEndpoint.java"
        context = _fixture_context(store, token_doc)
        checks = {
            "document_present": context["document_present"],
        }
        return {
            "fixture_id": fixture_id,
            "pass": all(checks.values()),
            "checks": checks,
            "details": {
                "status": "legacy placeholder validation only",
            },
        }

    raise ValueError(f"unsupported fixture: {fixture_id}")
