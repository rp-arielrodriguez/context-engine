from __future__ import annotations

from context_engine.adapters.semantics.spring import (
    _candidate_resolution_metadata,
    _eliminate_impossible_candidates,
    _prefer_candidates,
)


def _make_candidate(
    bean_name: str,
    *,
    profiles: set[str] | None = None,
    negative_profiles: set[str] | None = None,
    is_primary: bool = False,
    conditional_on_missing: bool = False,
) -> dict:
    return {
        "bean_id": f"springbean:{bean_name}",
        "symbol": f"test/{bean_name}#",
        "document": f"src/{bean_name}.java",
        "fqcn": "com.example.SomeService",
        "simple_name": "SomeService",
        "bean_name": bean_name,
        "profiles": profiles or set(),
        "negative_profiles": negative_profiles or set(),
        "is_primary": is_primary,
        "conditional_on_missing": conditional_on_missing,
    }


def test_eliminate_removes_negative_profile_conflicts() -> None:
    candidates = [
        _make_candidate("implA", profiles={"spring-web"}, is_primary=True),
        _make_candidate("legacyImpl", negative_profiles={"spring-web"}),
    ]
    result = _eliminate_impossible_candidates(candidates, consumer_profiles={"spring-web"})

    assert len(result) == 1
    assert result[0]["bean_name"] == "implA"


def test_eliminate_removes_conditional_when_non_conditional_exists() -> None:
    candidates = [
        _make_candidate("primary", is_primary=True),
        _make_candidate("fallback", conditional_on_missing=True),
    ]
    result = _eliminate_impossible_candidates(candidates, consumer_profiles=set())

    assert len(result) == 1
    assert result[0]["bean_name"] == "primary"


def test_eliminate_keeps_conditional_when_all_conditional() -> None:
    candidates = [
        _make_candidate("a", conditional_on_missing=True),
        _make_candidate("b", conditional_on_missing=True),
    ]
    result = _eliminate_impossible_candidates(candidates, consumer_profiles=set())

    assert len(result) == 2


def test_eliminate_chain_profile_then_conditional() -> None:
    """The RAF case: three candidates, only one survives both eliminations."""
    candidates = [
        _make_candidate("requestInfoServiceImpl", profiles={"spring-web"}, is_primary=True),
        _make_candidate("getRequestInfoServiceLegacy", negative_profiles={"spring-web"}, conditional_on_missing=True),
        _make_candidate("requestInfoServiceImpl2", conditional_on_missing=True),
    ]
    result = _eliminate_impossible_candidates(candidates, consumer_profiles={"spring-web"})

    assert len(result) == 1
    assert result[0]["bean_name"] == "requestInfoServiceImpl"


def test_eliminate_falls_back_when_all_removed() -> None:
    candidates = [
        _make_candidate("only", negative_profiles={"web"}),
    ]
    result = _eliminate_impossible_candidates(candidates, consumer_profiles={"web"})

    # safety fallback: return original rather than empty
    assert len(result) == 1
    assert result[0]["bean_name"] == "only"


def test_eliminate_noop_without_consumer_profiles() -> None:
    candidates = [
        _make_candidate("a", negative_profiles={"web"}),
        _make_candidate("b"),
    ]
    result = _eliminate_impossible_candidates(candidates, consumer_profiles=None)

    assert len(result) == 2


def test_prefer_candidates_with_qualifier_overrides_scoring() -> None:
    candidates = [
        _make_candidate("highScore", is_primary=True),
        _make_candidate("qualifiedBean"),
    ]
    result = _prefer_candidates(candidates, qualifier_hint="qualifiedBean")

    assert len(result) == 1
    assert result[0]["bean_name"] == "qualifiedBean"


def test_prefer_candidates_resolves_raf_case() -> None:
    """End-to-end: the RAF disambiguation should produce a single winner."""
    candidates = [
        _make_candidate("requestInfoServiceImpl", profiles={"spring-web"}, is_primary=True),
        _make_candidate("getRequestInfoServiceLegacy", negative_profiles={"spring-web"}, conditional_on_missing=True),
        _make_candidate("requestInfoServiceImpl_common", conditional_on_missing=True),
    ]
    result = _prefer_candidates(candidates, bean_name_hint="requestInfoService", consumer_profiles={"spring-web"})

    assert len(result) == 1
    assert result[0]["bean_name"] == "requestInfoServiceImpl"

    meta = _candidate_resolution_metadata(result)
    assert meta["match_state"] == "resolved"
    assert meta["candidate_count"] == 1


def test_prefer_candidates_still_reports_ambiguous_when_tied() -> None:
    candidates = [
        _make_candidate("implA"),
        _make_candidate("implB"),
    ]
    result = _prefer_candidates(candidates, consumer_profiles=set())

    # both score the same, no elimination possible
    assert len(result) == 2

    meta = _candidate_resolution_metadata(result)
    assert meta["match_state"] == "ambiguous"
