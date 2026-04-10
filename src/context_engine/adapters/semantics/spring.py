from __future__ import annotations


def build_spring_edges(store) -> list[dict]:
    edges: list[dict] = []
    bean_candidates_by_type: dict[str, list[dict]] = {}

    for document, doc_symbols in store.symbols_by_document.items():
        defs = store._definitions_by_document(document)
        doc_occurrences = store.occurrences_by_document.get(document, [])
        source = store._read_source(document)
        import_map = store._extract_import_map(source)

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
                bean_meta = {
                    "bean_id": bean_id,
                    "symbol": matching_method.symbol,
                    "document": document,
                    "fqcn": fqcn,
                    "simple_name": store._simple_name_from_fqcn(fqcn),
                    "bean_name": method_name,
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
                            candidates = bean_candidates_by_type.get(fqcn, [])
                            if candidates:
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
                                            },
                                        }
                                    )
                        continue

            simple_type = type_name.split("<", 1)[0] if type_name else ""
            fqcn = import_map.get(simple_type, simple_type)
            candidates = bean_candidates_by_type.get(fqcn, []) if fqcn else []

            if candidates:
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
            candidates = bean_candidates_by_type.get(fqcn, [])
            if not candidates:
                continue
            resolution = "constructor-final-field-type" if field_name in final_fields else "annotated-field-type"
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
                        },
                    }
                )

        for ctor in constructor_symbols:
            owner_symbol = class_by_constructor.get(ctor.symbol)
            owner = store.symbols_by_id.get(owner_symbol) if owner_symbol else None
            if not owner:
                continue
            params = store._extract_constructor_params(source, owner.display_name)
            for _, ctor_type in params:
                simple_type = ctor_type.split("<", 1)[0]
                fqcn = import_map.get(simple_type, simple_type)
                candidates = bean_candidates_by_type.get(fqcn, [])
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
                            },
                        }
                    )

        for cls in class_symbols:
            deps_added: set[tuple[str, str]] = set()
            for field_name, field_type in field_types.items():
                simple_type = field_type.split("<", 1)[0]
                fqcn = import_map.get(simple_type, simple_type)
                candidates = bean_candidates_by_type.get(fqcn, [])
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
                            },
                        }
                    )

    return edges
