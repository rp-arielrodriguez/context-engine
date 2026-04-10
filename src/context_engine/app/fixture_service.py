from __future__ import annotations

from .flow_helpers import has_operator


MONO_SYMBOL = "semanticdb maven . . reactor/core/publisher/Mono#"


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
        has_doc = controller_doc in store.documents_by_path
        has_method = method_symbol in store.symbols_by_id
        refs_to_mono = [r for r in store.references_by_symbol.get(MONO_SYMBOL, []) if r.document == controller_doc]
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
            "reactor_returns_publisher": len(store.get_semantic_edges(method_symbol, direction="out", type_filter=["reactor.returns_publisher"])) > 0,
            "reactor_operator_chain": len(store.get_semantic_edges(return_stage, direction="out", type_filter=["reactor.operator_applies"])) > 0,
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
        refs_to_mono = [r for r in store.references_by_symbol.get(MONO_SYMBOL, []) if r.document == controller_doc]

        checks = {
            "document_present": controller_doc in store.documents_by_path,
            "method_symbol_present": method_symbol in store.symbols_by_id,
            "spring_component_declares": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.component_declares"])) > 0,
            "spring_endpoint_maps_to": len(store.get_semantic_edges(method_symbol, direction="in", type_filter=["spring.endpoint_maps_to"])) > 0,
            "spring_depends_on_resolved": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.depends_on"])) > 0,
            "spring_injects_resolved": len(store.get_semantic_edges(field_symbol, direction="out", type_filter=["spring.injects"])) > 0,
            "mono_reference_in_controller": len(refs_to_mono) > 0,
            "reactor_returns_publisher": len(store.get_semantic_edges(method_symbol, direction="out", type_filter=["reactor.returns_publisher"])) > 0,
            "reactor_just_or_empty": has_operator(store, return_stage, "justOrEmpty"),
            "reactor_map": has_operator(store, return_stage, "map"),
            "reactor_default_if_empty": has_operator(store, return_stage, "defaultIfEmpty"),
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
        refs_to_mono = [r for r in store.references_by_symbol.get(MONO_SYMBOL, []) if r.document == service_doc]

        checks = {
            "document_present": service_doc in store.documents_by_path,
            "class_symbol_present": class_symbol in store.symbols_by_id,
            "method_symbol_present": method_symbol in store.symbols_by_id,
            "spring_component_declares": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.component_declares"])) > 0,
            "spring_depends_on_resolved": len(store.get_semantic_edges(class_symbol, direction="out", type_filter=["spring.depends_on"])) > 0,
            "spring_injects_resolved": len(store.get_semantic_edges(field_symbol, direction="out", type_filter=["spring.injects"])) > 0,
            "mono_reference_in_service": len(refs_to_mono) > 0,
            "reactor_returns_publisher": len(store.get_semantic_edges(method_symbol, direction="out", type_filter=["reactor.returns_publisher"])) > 0,
            "reactor_from_callable": has_operator(store, return_stage, "fromCallable"),
            "reactor_do_on_error": has_operator(store, return_stage, "doOnError"),
            "reactor_on_error_map": has_operator(store, return_stage, "onErrorMap"),
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
        checks = {
            "document_present": token_doc in store.documents_by_path,
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
