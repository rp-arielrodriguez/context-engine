from __future__ import annotations

import re


def _extract_profile_hints(source: str) -> tuple[set[str], set[str]]:
    positive: set[str] = set()
    negative: set[str] = set()
    for match in re.finditer(r'@Profile\(([^)]*)\)', source):
        raw = match.group(1)
        for quoted in re.findall(r'"([^"]+)"', raw):
            profile = quoted.strip()
            if not profile:
                continue
            if profile.startswith("!"):
                negative.add(profile[1:])
            else:
                positive.add(profile)
    return positive, negative


def _extract_method_annotation_block(source: str, method_name: str) -> str:
    lines = source.splitlines()
    for idx, line in enumerate(lines):
        if re.search(rf'\b{re.escape(method_name)}\s*\(', line):
            start = idx
            while start > 0 and lines[start - 1].strip().startswith("@"):
                start -= 1
            return "\n".join(lines[start : idx + 1])
    return ""


def _score_candidate(candidate: dict, *, consumer_profiles: set[str], bean_name_hint: str | None) -> int:
    score = 0

    bean_name = candidate.get("bean_name", "")
    if bean_name_hint:
        if bean_name == bean_name_hint:
            score += 10
        elif bean_name.lower().endswith(bean_name_hint.lower()):
            score += 4

    candidate_profiles = set(candidate.get("profiles", set()))
    candidate_negative_profiles = set(candidate.get("negative_profiles", set()))
    if consumer_profiles:
        if candidate_profiles & consumer_profiles:
            score += 6
        if candidate_negative_profiles & consumer_profiles:
            score -= 8

    if candidate.get("is_primary"):
        score += 5
    if candidate.get("conditional_on_missing"):
        score -= 2
    if candidate.get("symbol", "").endswith("#"):
        score += 1

    return score


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for candidate in candidates:
        bean_id = candidate["bean_id"]
        if bean_id in seen:
            continue
        seen.add(bean_id)
        out.append(candidate)
    return out


def _candidate_match_state(candidates: list[dict]) -> str:
    if not candidates:
        return "unresolved"
    if len(candidates) == 1:
        return "resolved"
    return "ambiguous"


def _candidate_resolution_metadata(candidates: list[dict]) -> dict:
    deduped = _dedupe_candidates(candidates)
    return {
        "match_state": _candidate_match_state(deduped),
        "candidate_count": len(deduped),
        "candidate_bean_names": sorted(
            {candidate.get("bean_name", "") for candidate in deduped if candidate.get("bean_name")}
        ),
    }


def _eliminate_impossible_candidates(
    candidates: list[dict],
    *,
    consumer_profiles: set[str] | None = None,
) -> list[dict]:
    """Remove candidates that Spring would never instantiate in this context.

    Two hard rules:
    1. Negative profile conflict: candidate has @Profile("!X") and consumer has X.
       Spring will not instantiate that bean -- it's not a preference, it's a fact.
    2. @ConditionalOnMissingBean: if a surviving non-conditional candidate exists
       for the same type, conditional candidates are superseded.

    Falls back to the original list if elimination removes everything.
    """
    if not candidates:
        return candidates
    profiles = consumer_profiles or set()

    # Pass 1: eliminate negative-profile conflicts
    after_profile: list[dict] = []
    for c in candidates:
        neg = set(c.get("negative_profiles", set()))
        if profiles and neg and neg & profiles:
            continue  # bean explicitly says "not with this profile"
        after_profile.append(c)
    if not after_profile:
        after_profile = candidates  # safety fallback

    # Pass 2: eliminate @ConditionalOnMissingBean when a non-conditional survives
    has_non_conditional = any(not c.get("conditional_on_missing") for c in after_profile)
    if has_non_conditional:
        after_conditional = [c for c in after_profile if not c.get("conditional_on_missing")]
        if after_conditional:
            after_profile = after_conditional

    return after_profile


def _prefer_candidates(
    candidates: list[dict],
    *,
    bean_name_hint: str | None = None,
    qualifier_hint: str | None = None,
    consumer_profiles: set[str] | None = None,
) -> list[dict]:
    candidates = _dedupe_candidates(candidates)
    if len(candidates) <= 1:
        return candidates

    consumer_profiles = consumer_profiles or set()

    # Stage 0: hard elimination of impossible candidates
    candidates = _eliminate_impossible_candidates(candidates, consumer_profiles=consumer_profiles)
    if len(candidates) <= 1:
        return candidates

    # Stage 1: @Qualifier / @Resource exact match (strongest signal)
    if qualifier_hint:
        exact_q = [c for c in candidates if c["bean_name"] == qualifier_hint]
        if exact_q:
            return exact_q

    # Stage 2: bean-name matching
    if bean_name_hint:
        exact = [candidate for candidate in candidates if candidate["bean_name"] == bean_name_hint]
        if exact:
            return exact

        suffix_matches = [candidate for candidate in candidates if candidate["bean_name"].lower().endswith(bean_name_hint.lower())]
        if suffix_matches:
            candidates = suffix_matches

    non_factory = [candidate for candidate in candidates if "#" in candidate["symbol"]]
    if non_factory:
        candidates = non_factory

    class_backed = [candidate for candidate in candidates if candidate["symbol"].endswith("#")]
    if class_backed:
        candidates = class_backed

    # Stage 3: score remaining survivors
    scored = [(_score_candidate(candidate, consumer_profiles=consumer_profiles, bean_name_hint=bean_name_hint), candidate) for candidate in candidates]
    best_score = max(score for score, _ in scored)
    best = [candidate for score, candidate in scored if score == best_score]
    return _dedupe_candidates(best)


def build_spring_edges(store) -> list[dict]:
    edges: list[dict] = []
    bean_candidates_by_type: dict[str, list[dict]] = {}

    for document, doc_symbols in store.symbols_by_document.items():
        defs = store._definitions_by_document(document)
        doc_occurrences = store.occurrences_by_document.get(document, [])
        source = store._read_source(document)
        import_map = store._extract_import_map(source)
        consumer_profiles, _ = _extract_profile_hints(source)

        component_ann = [o for o in doc_occurrences if store._is_spring_component_annotation(o.symbol)]
        mapping_ann = [o for o in doc_occurrences if store._is_spring_mapping_annotation(o.symbol)]
        inject_ann = [o for o in doc_occurrences if store._is_injection_annotation(o.symbol)]

        class_symbols = [s for s in doc_symbols if s.kind == "Class"]
        method_symbols = [s for s in doc_symbols if s.kind in {"Method", "StaticMethod"}]
        constructor_symbols = [s for s in doc_symbols if s.kind == "Constructor"]

        for cls in class_symbols:
            cls_def = defs.get(cls.symbol)
            if not cls_def:
                continue
            cls_line = cls_def.range[0] if cls_def.range else -1
            near = [
                a
                for a in component_ann
                if a.range and a.range[0] <= cls_line and (cls_line - a.range[0]) <= 12
            ]
            if not near:
                continue
            bean_id = f"springbean:{cls.symbol}"
            edge = {
                "source": cls.symbol,
                "target": bean_id,
                "type": "spring.component_declares",
                "provenance": "spring-derived",
                "confidence": 1.0,
                "metadata": {
                    "document": document,
                    "annotations": sorted({a.symbol for a in near}),
                },
            }
            edges.append(edge)

            cls_fqcn = store._fqcn_from_symbol(cls.symbol)
            if cls_fqcn and not store._is_test_document(document):
                bean_meta = {
                    "bean_id": bean_id,
                    "symbol": cls.symbol,
                    "document": document,
                    "fqcn": cls_fqcn,
                    "simple_name": store._simple_name_from_fqcn(cls_fqcn),
                    "bean_name": store._bean_name_for_class(cls_fqcn),
                }
                bean_candidates_by_type.setdefault(cls_fqcn, []).append(bean_meta)

                for interface_name in store._extract_implemented_interfaces(source, cls.display_name):
                    interface_fqcn = import_map.get(interface_name, interface_name)
                    bean_candidates_by_type.setdefault(interface_fqcn, []).append(bean_meta)

        bean_methods = store._extract_bean_methods(source)
        for method_name, return_type in bean_methods:
            matching_method = next((m for m in method_symbols if m.display_name == method_name), None)
            if not matching_method:
                continue
            bean_id = f"springbean:{matching_method.symbol}"
            edges.append(
                {
                    "source": matching_method.symbol,
                    "target": bean_id,
                    "type": "spring.bean_factory_produces",
                    "provenance": "spring-derived",
                    "confidence": 0.95,
                    "metadata": {
                        "document": document,
                        "return_type": import_map.get(return_type, return_type),
                    },
                }
            )
            fqcn = import_map.get(return_type, return_type)
            if not store._is_test_document(document):
                annotation_block = _extract_method_annotation_block(source, method_name)
                positive_profiles, negative_profiles = _extract_profile_hints(annotation_block)
                bean_meta = {
                    "bean_id": bean_id,
                    "symbol": matching_method.symbol,
                    "document": document,
                    "fqcn": fqcn,
                    "simple_name": store._simple_name_from_fqcn(fqcn),
                    "bean_name": method_name,
                    "profiles": positive_profiles,
                    "negative_profiles": negative_profiles,
                    "is_primary": "@Primary" in annotation_block,
                    "conditional_on_missing": "@ConditionalOnMissingBean" in annotation_block,
                }
                bean_candidates_by_type.setdefault(fqcn, []).append(bean_meta)

        for method in method_symbols:
            mdef = defs.get(method.symbol)
            if not mdef:
                continue
            mline = mdef.range[0] if mdef.range else -1
            near = [a for a in mapping_ann if a.range and (mline - 3) <= a.range[0] <= (mline + 1)]
            if not near:
                continue
            http_node = f"http_entrypoint:{document}:{method.display_name}:{mline}"
            edges.append(
                {
                    "source": http_node,
                    "target": method.symbol,
                    "type": "spring.endpoint_maps_to",
                    "provenance": "spring-derived",
                    "confidence": 1.0,
                    "metadata": {
                        "document": document,
                        "method": method.display_name,
                        "annotations": sorted({a.symbol for a in near}),
                    },
                }
            )

        method_by_scope = {
            tuple(defs[s.symbol].enclosing_range): s.symbol
            for s in (method_symbols + constructor_symbols)
            if s.symbol in defs and defs[s.symbol].enclosing_range
        }

        field_types = store._extract_field_types(source)
        final_fields = store._extract_final_fields(source)

        class_by_constructor: dict[str, str] = {}
        for ctor in constructor_symbols:
            ctor_def = defs.get(ctor.symbol)
            if not ctor_def or not ctor_def.range:
                continue
            class_owner = next(
                (
                    cls
                    for cls in class_symbols
                    if defs.get(cls.symbol)
                    and defs[cls.symbol].range
                    and defs[cls.symbol].range[0] <= ctor_def.range[0]
                ),
                None,
            )
            if class_owner is None:
                continue
            class_by_constructor[ctor.symbol] = class_owner.symbol

        field_by_symbol = {s.symbol: s.display_name for s in doc_symbols if s.kind == "Field"}

        for ann in inject_ann:
            site_symbol = ""
            if ann.enclosing_range:
                site_symbol = method_by_scope.get(tuple(ann.enclosing_range), "")
            if not site_symbol:
                ann_line = ann.range[0] if ann.range else -1
                field_candidates = []
                for s in doc_symbols:
                    if s.kind != "Field":
                        continue
                    sdef = defs.get(s.symbol)
                    if not sdef or not sdef.range:
                        continue
                    line = sdef.range[0]
                    if abs(line - ann_line) <= 2:
                        field_candidates.append((abs(line - ann_line), s.symbol))
                if field_candidates:
                    field_candidates.sort(key=lambda t: t[0])
                    site_symbol = field_candidates[0][1]
            if not site_symbol:
                continue

            ann_line = ann.range[0] if ann.range else -1
            type_name = ""
            if site_symbol in field_by_symbol:
                type_name = field_types.get(field_by_symbol[site_symbol], "")

            if not type_name and site_symbol in class_by_constructor:
                owner_symbol = class_by_constructor[site_symbol]
                owner = store.symbols_by_id.get(owner_symbol)
                if owner:
                    params = store._extract_constructor_params(source, owner.display_name)
                    if params:
                        for _, ctor_type in params:
                            fqcn = import_map.get(ctor_type.split("<", 1)[0], ctor_type.split("<", 1)[0])
                            candidates = _prefer_candidates(bean_candidates_by_type.get(fqcn, []), consumer_profiles=consumer_profiles)
                            if candidates:
                                resolution_metadata = _candidate_resolution_metadata(candidates)
                                for candidate in candidates:
                                    edges.append(
                                        {
                                            "source": owner_symbol,
                                            "target": candidate["bean_id"],
                                            "type": "spring.depends_on",
                                            "provenance": "spring-derived",
                                            "confidence": 0.75,
                                            "metadata": {
                                                "document": document,
                                                "annotation": ann.symbol,
                                                "resolution": "by-constructor-type",
                                                "required_type": fqcn,
                                                **resolution_metadata,
                                            },
                                        }
                                    )
                        continue

            simple_type = type_name.split("<", 1)[0] if type_name else ""
            fqcn = import_map.get(simple_type, simple_type)
            bean_name_hint = field_by_symbol.get(site_symbol) if site_symbol in field_by_symbol else None
            qualifier_hint = store._extract_qualifier_hint(source, bean_name_hint) if bean_name_hint else None
            candidates = _prefer_candidates(
                bean_candidates_by_type.get(fqcn, []),
                bean_name_hint=bean_name_hint,
                qualifier_hint=qualifier_hint,
                consumer_profiles=consumer_profiles,
            ) if fqcn else []

            if candidates:
                resolution_metadata = _candidate_resolution_metadata(candidates)
                for candidate in candidates:
                    edges.append(
                        {
                            "source": site_symbol,
                            "target": candidate["bean_id"],
                            "type": "spring.injects",
                            "provenance": "spring-derived",
                            "confidence": 0.85,
                            "metadata": {
                                "document": document,
                                "annotation": ann.symbol,
                                "resolution": "by-imported-type",
                                "required_type": fqcn,
                                "bean_name": candidate["bean_name"],
                                **resolution_metadata,
                            },
                        }
                    )
            else:
                unresolved = f"springbean:unresolved:{document}:{ann_line}"
                edges.append(
                    {
                        "source": site_symbol,
                        "target": unresolved,
                        "type": "spring.injects",
                        "provenance": "spring-derived",
                        "confidence": 0.4,
                        "metadata": {
                            "document": document,
                            "annotation": ann.symbol,
                            "resolution": "unresolved",
                            "required_type": fqcn,
                            "match_state": "unresolved",
                            "candidate_count": 0,
                            "candidate_bean_names": [],
                        },
                    }
                )

        for field_symbol, field_name in field_by_symbol.items():
            field_type = field_types.get(field_name, "")
            if not field_type:
                continue
            explicit_or_constructor = field_name in final_fields or store._field_has_nearby_inject_annotation(source, field_name)
            if not explicit_or_constructor:
                continue
            simple_type = field_type.split("<", 1)[0]
            fqcn = import_map.get(simple_type, simple_type)
            qualifier_hint = store._extract_qualifier_hint(source, field_name)
            candidates = _prefer_candidates(
                bean_candidates_by_type.get(fqcn, []),
                bean_name_hint=field_name,
                qualifier_hint=qualifier_hint,
                consumer_profiles=consumer_profiles,
            )
            if not candidates:
                continue
            resolution = "constructor-final-field-type" if field_name in final_fields else "annotated-field-type"
            resolution_metadata = _candidate_resolution_metadata(candidates)
            for candidate in candidates:
                edges.append(
                    {
                        "source": field_symbol,
                        "target": candidate["bean_id"],
                        "type": "spring.injects",
                        "provenance": "spring-derived",
                        "confidence": 0.8 if field_name in final_fields else 0.85,
                        "metadata": {
                            "document": document,
                            "resolution": resolution,
                            "required_type": fqcn,
                            "field_name": field_name,
                            "bean_name": candidate["bean_name"],
                            **resolution_metadata,
                        },
                    }
                )

        for ctor in constructor_symbols:
            owner_symbol = class_by_constructor.get(ctor.symbol)
            owner = store.symbols_by_id.get(owner_symbol) if owner_symbol else None
            if not owner:
                continue
            params = store._extract_constructor_params(source, owner.display_name)
            ctor_qualifier_hints = store._extract_constructor_qualifier_hints(source, owner.display_name)
            for param_name, ctor_type in params:
                simple_type = ctor_type.split("<", 1)[0]
                fqcn = import_map.get(simple_type, simple_type)
                candidates = _prefer_candidates(
                    bean_candidates_by_type.get(fqcn, []),
                    qualifier_hint=ctor_qualifier_hints.get(param_name),
                    consumer_profiles=consumer_profiles,
                )
                resolution_metadata = _candidate_resolution_metadata(candidates)
                for candidate in candidates:
                    edges.append(
                        {
                            "source": owner_symbol,
                            "target": candidate["bean_id"],
                            "type": "spring.depends_on",
                            "provenance": "spring-derived",
                            "confidence": 0.7,
                            "metadata": {
                                "document": document,
                                "resolution": "constructor-parameter-type",
                                "required_type": fqcn,
                                "bean_name": candidate["bean_name"],
                                **resolution_metadata,
                            },
                        }
                    )

        for cls in class_symbols:
            deps_added: set[tuple[str, str]] = set()
            for field_name, field_type in field_types.items():
                simple_type = field_type.split("<", 1)[0]
                fqcn = import_map.get(simple_type, simple_type)
                candidates = _prefer_candidates(
                    bean_candidates_by_type.get(fqcn, []),
                    bean_name_hint=field_name,
                    qualifier_hint=store._extract_qualifier_hint(source, field_name),
                    consumer_profiles=consumer_profiles,
                )
                resolution_metadata = _candidate_resolution_metadata(candidates)
                for candidate in candidates:
                    key = (cls.symbol, candidate["bean_id"])
                    if key in deps_added:
                        continue
                    deps_added.add(key)
                    edges.append(
                        {
                            "source": cls.symbol,
                            "target": candidate["bean_id"],
                            "type": "spring.depends_on",
                            "provenance": "spring-derived",
                            "confidence": 0.65,
                            "metadata": {
                                "document": document,
                                "resolution": "final-field-type",
                                "required_type": fqcn,
                                "field_name": field_name,
                                "bean_name": candidate["bean_name"],
                                **resolution_metadata,
                            },
                        }
                    )

    return edges
