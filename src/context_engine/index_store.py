from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote, urlparse

from .app.fixture_service import validate_fixture as validate_fixture_with_store
from .app.mixed_flow_service import get_mixed_flow as get_mixed_flow_with_store
from .adapters.semantics.netty import build_netty_edges
from .adapters.semantics.reactor import build_reactor_edges
from .adapters.semantics.spring import build_spring_edges
from .adapters.semantics.helpers import (
    bean_name_for_class,
    contains_scope,
    extract_bean_methods,
    extract_constructor_params,
    extract_field_types,
    extract_final_fields,
    extract_implemented_interfaces,
    extract_import_map,
    field_has_nearby_inject_annotation,
    fqcn_from_symbol,
    is_injection_annotation,
    is_reactor_publisher_symbol,
    is_spring_component_annotation,
    is_spring_mapping_annotation,
    is_test_document,
    normalize_range,
    reactor_operator_name,
    scope_size,
    simple_name_from_fqcn,
)
from .core.models import (
    DocumentRecord,
    IndexMetadata,
    OccurrenceRecord,
    SymbolRecord,
)


class IndexStore:
    _normalize_range = staticmethod(normalize_range)
    _scope_size = staticmethod(scope_size)
    _contains = staticmethod(contains_scope)
    _is_spring_component_annotation = staticmethod(is_spring_component_annotation)
    _is_spring_mapping_annotation = staticmethod(is_spring_mapping_annotation)
    _is_injection_annotation = staticmethod(is_injection_annotation)
    _fqcn_from_symbol = staticmethod(fqcn_from_symbol)
    _simple_name_from_fqcn = staticmethod(simple_name_from_fqcn)
    _bean_name_for_class = staticmethod(bean_name_for_class)
    _extract_import_map = staticmethod(extract_import_map)
    _extract_constructor_params = staticmethod(extract_constructor_params)
    _extract_field_types = staticmethod(extract_field_types)
    _extract_final_fields = staticmethod(extract_final_fields)
    _field_has_nearby_inject_annotation = staticmethod(field_has_nearby_inject_annotation)
    _is_test_document = staticmethod(is_test_document)
    _extract_implemented_interfaces = staticmethod(extract_implemented_interfaces)
    _extract_bean_methods = staticmethod(extract_bean_methods)
    _is_reactor_publisher_symbol = staticmethod(is_reactor_publisher_symbol)
    _reactor_operator_name = staticmethod(reactor_operator_name)

    @staticmethod
    def _normalize_symbol(symbol: str, document: str) -> str:
        if symbol.startswith("local "):
            return f"{symbol}@@{document}"
        return symbol

    def __init__(
        self,
        metadata: IndexMetadata,
        documents: list[DocumentRecord],
        symbols: list[SymbolRecord],
        occurrences: list[OccurrenceRecord],
    ) -> None:
        self.metadata = metadata
        self.documents = documents
        self.symbols = symbols
        self.occurrences = occurrences

        self.documents_by_path = {d.path: d for d in documents}
        self.symbols_by_id = {s.symbol: s for s in symbols}
        self.occurrences_by_document: dict[str, list[OccurrenceRecord]] = {}
        self._source_cache: dict[str, str] = {}

        self.symbols_by_display: dict[str, list[SymbolRecord]] = {}
        self.symbols_by_document: dict[str, list[SymbolRecord]] = {}
        for s in symbols:
            key = s.display_name.lower()
            self.symbols_by_display.setdefault(key, []).append(s)
            self.symbols_by_document.setdefault(s.document, []).append(s)

        self.occurrences_by_symbol: dict[str, list[OccurrenceRecord]] = {}
        self.references_by_symbol: dict[str, list[OccurrenceRecord]] = {}
        self.definitions_by_symbol: dict[str, list[OccurrenceRecord]] = {}

        self.calls_out_by_symbol: dict[str, set[str]] = {}
        self.calls_in_by_symbol: dict[str, set[str]] = {}
        self.occurrences_by_caller: dict[str, list[OccurrenceRecord]] = {}

        self.method_symbol_by_scope: dict[tuple[str, tuple[int, ...]], str] = {}
        self.method_scopes_by_doc: dict[str, list[tuple[tuple[int, int, int, int], str]]] = {}

        method_kinds = {"Method", "StaticMethod", "Constructor"}

        for o in occurrences:
            if o.is_definition and o.kind in method_kinds and o.enclosing_range:
                key = (o.document, tuple(o.enclosing_range))
                self.method_symbol_by_scope[key] = o.symbol
                normalized = self._normalize_range(o.enclosing_range)
                if normalized:
                    self.method_scopes_by_doc.setdefault(o.document, []).append((normalized, o.symbol))

        for doc in self.method_scopes_by_doc:
            self.method_scopes_by_doc[doc].sort(key=lambda item: self._scope_size(item[0]))

        for o in occurrences:
            self.occurrences_by_symbol.setdefault(o.symbol, []).append(o)
            self.occurrences_by_document.setdefault(o.document, []).append(o)
            if o.is_definition:
                self.definitions_by_symbol.setdefault(o.symbol, []).append(o)
            else:
                self.references_by_symbol.setdefault(o.symbol, []).append(o)

        self._build_call_graph()
        spring_edges = self._build_spring_edges()
        reactor_edges = self._build_reactor_edges(spring_edges)
        netty_edges = self._build_netty_edges(spring_edges, reactor_edges)
        self.semantic_edges = spring_edges + reactor_edges + netty_edges
        self.semantic_edges_by_source: dict[str, list[dict]] = {}
        self.semantic_edges_by_target: dict[str, list[dict]] = {}
        for edge in self.semantic_edges:
            self.semantic_edges_by_source.setdefault(edge["source"], []).append(edge)
            self.semantic_edges_by_target.setdefault(edge["target"], []).append(edge)

    def _build_call_graph(self) -> None:
        for o in self.occurrences:
            if o.is_definition:
                continue
            caller = None

            if o.enclosing_range:
                caller = self.method_symbol_by_scope.get((o.document, tuple(o.enclosing_range)))

            if caller is None:
                caller = self._infer_caller_by_position(o)

            if not caller:
                continue
            callee = o.symbol
            if not callee:
                continue
            if callee.startswith("local "):
                continue
            if caller == callee:
                continue
            self.occurrences_by_caller.setdefault(caller, []).append(o)
            self.calls_out_by_symbol.setdefault(caller, set()).add(callee)
            self.calls_in_by_symbol.setdefault(callee, set()).add(caller)

    def _infer_caller_by_position(self, occurrence: OccurrenceRecord) -> str | None:
        pos = self._normalize_range(occurrence.range)
        if not pos:
            return None
        line, col = pos[0], pos[1]
        scopes = self.method_scopes_by_doc.get(occurrence.document, [])
        for scope, symbol in scopes:
            if self._contains(scope, line, col):
                return symbol
        return None

    def _definitions_by_document(self, document: str) -> dict[str, OccurrenceRecord]:
        out: dict[str, OccurrenceRecord] = {}
        for symbol in [s.symbol for s in self.symbols_by_document.get(document, [])]:
            defs = self.definitions_by_symbol.get(symbol, [])
            if defs:
                out[symbol] = defs[0]
        return out

    def _project_root_path(self) -> Path | None:
        root = self.metadata.project_root or ""
        if not root:
            return None
        if root.startswith("file://"):
            parsed = urlparse(root)
            return Path(unquote(parsed.path))
        return Path(root)

    def _read_source(self, document: str) -> str:
        if document in self._source_cache:
            return self._source_cache[document]
        root = self._project_root_path()
        if root is None:
            self._source_cache[document] = ""
            return ""
        path = root / document
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            text = ""
        self._source_cache[document] = text
        return text

    def _method_occurrences(self, method_symbol: str) -> list[OccurrenceRecord]:
        occs = self.occurrences_by_caller.get(method_symbol, [])
        return sorted(occs, key=lambda o: (o.range, o.symbol))

    def _build_spring_edges(self) -> list[dict]:
        return build_spring_edges(self)

    def _build_reactor_edges(self, spring_edges: list[dict]) -> list[dict]:
        return build_reactor_edges(self, spring_edges)

    def _build_netty_edges(self, spring_edges: list[dict], reactor_edges: list[dict]) -> list[dict]:
        return build_netty_edges(spring_edges, reactor_edges)

    @classmethod
    def from_ndjson(cls, ndjson_path: Path) -> "IndexStore":
        metadata: IndexMetadata | None = None
        documents: list[DocumentRecord] = []
        symbols: list[SymbolRecord] = []
        occurrences: list[OccurrenceRecord] = []

        with ndjson_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                typ = row.get("type")

                if typ == "meta":
                    metadata = IndexMetadata(
                        project_root=row.get("project_root", ""),
                        tool_name=row.get("tool_name", ""),
                        tool_version=row.get("tool_version", ""),
                        documents_count=int(row.get("documents_count", 0)),
                        external_symbols_count=int(row.get("external_symbols_count", 0)),
                    )
                elif typ == "document":
                    documents.append(
                        DocumentRecord(
                            path=row["path"],
                            language=row.get("language", ""),
                            symbols_count=int(row.get("symbols_count", 0)),
                            occurrences_count=int(row.get("occurrences_count", 0)),
                        )
                    )
                elif typ == "symbol":
                    document = row.get("document", "")
                    symbol = cls._normalize_symbol(row["symbol"], document)
                    enclosing_raw = row.get("enclosing_symbol", "")
                    enclosing_symbol = cls._normalize_symbol(enclosing_raw, document) if enclosing_raw else ""
                    symbols.append(
                        SymbolRecord(
                            symbol=symbol,
                            display_name=row.get("display_name", ""),
                            enclosing_symbol=enclosing_symbol,
                            kind=row.get("kind", ""),
                            document=document,
                        )
                    )
                elif typ == "occurrence":
                    roles = row.get("roles", {})
                    document = row.get("document", "")
                    symbol = cls._normalize_symbol(row.get("symbol", ""), document)
                    enclosing_raw = row.get("enclosing_symbol", "")
                    enclosing_symbol = cls._normalize_symbol(enclosing_raw, document) if enclosing_raw else ""
                    occurrences.append(
                        OccurrenceRecord(
                            symbol=symbol,
                            display_name=row.get("display_name", ""),
                            enclosing_symbol=enclosing_symbol,
                            kind=row.get("kind", ""),
                            document=document,
                            range=[int(x) for x in row.get("range", [])],
                            enclosing_range=[int(x) for x in row.get("enclosing_range", [])],
                            symbol_roles=int(row.get("symbol_roles", 0)),
                            is_definition=bool(roles.get("definition", False)),
                            is_import=bool(roles.get("import", False)),
                            is_write=bool(roles.get("write", False)),
                            is_read=bool(roles.get("read", False)),
                            is_generated=bool(roles.get("generated", False)),
                            is_test=bool(roles.get("test", False)),
                            is_forward_definition=bool(roles.get("forward_definition", False)),
                        )
                    )

        if metadata is None:
            raise ValueError(f"No meta row found in {ndjson_path}")

        if not documents and metadata.documents_count > 0:
            raise ValueError(
                f"NDJSON appears truncated or invalid (meta says {metadata.documents_count} documents, parsed 0): {ndjson_path}"
            )

        return cls(metadata, documents, symbols, occurrences)

    def find_documents(self, query: str, limit: int = 20) -> list[dict]:
        q = query.lower()
        out = [d for d in self.documents if q in d.path.lower()]
        out.sort(key=lambda d: d.path)
        return [asdict(d) for d in out[:limit]]

    def find_symbols(self, query: str, path_filter: str | None = None, limit: int = 20) -> list[dict]:
        q = query.lower()
        path_q = path_filter.lower() if path_filter else None
        matches: list[SymbolRecord] = []
        for s in self.symbols:
            if path_q and path_q not in s.document.lower():
                continue
            if q in s.display_name.lower() or q in s.symbol.lower():
                matches.append(s)
        matches.sort(key=lambda s: (s.display_name, s.document, s.symbol))
        return [asdict(s) for s in matches[:limit]]

    def get_symbol(self, symbol_id: str) -> dict:
        symbol = self.symbols_by_id.get(symbol_id)
        if symbol is None:
            raise KeyError(f"symbol not found: {symbol_id}")

        occurrences = self.occurrences_by_symbol.get(symbol_id, [])
        definitions = self.definitions_by_symbol.get(symbol_id, [])
        references = self.references_by_symbol.get(symbol_id, [])

        called_symbols = sorted(self.calls_out_by_symbol.get(symbol_id, set()))
        caller_symbols = sorted(self.calls_in_by_symbol.get(symbol_id, set()))

        return {
            "symbol": asdict(symbol),
            "definitions_count": len(definitions),
            "references_count": len(references),
            "documents_count": len({o.document for o in occurrences}),
            "calls_out_count": len(called_symbols),
            "calls_in_count": len(caller_symbols),
        }

    def get_occurrences(self, symbol_id: str, path_filter: str | None = None, limit: int = 100) -> list[dict]:
        path_q = path_filter.lower() if path_filter else None
        occs = self.occurrences_by_symbol.get(symbol_id, [])
        if path_q:
            occs = [o for o in occs if path_q in o.document.lower()]
        occs = sorted(occs, key=lambda o: (o.document, o.range))
        return [asdict(o) for o in occs[:limit]]

    def get_references(self, symbol_id: str, path_filter: str | None = None, limit: int = 100) -> list[dict]:
        path_q = path_filter.lower() if path_filter else None
        refs = self.references_by_symbol.get(symbol_id, [])
        if path_q:
            refs = [r for r in refs if path_q in r.document.lower()]
        refs = sorted(refs, key=lambda o: (o.document, o.range))
        return [asdict(o) for o in refs[:limit]]

    def get_semantic_edges(
        self,
        node_id: str,
        direction: str = "both",
        provenance_filter: list[str] | None = None,
        type_filter: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        edges: list[dict] = []
        if direction in {"out", "both"}:
            edges.extend(self.semantic_edges_by_source.get(node_id, []))
        if direction in {"in", "both"}:
            edges.extend(self.semantic_edges_by_target.get(node_id, []))

        if provenance_filter:
            allowed = set(provenance_filter)
            edges = [e for e in edges if e.get("provenance") in allowed]
        if type_filter:
            allowed_t = set(type_filter)
            edges = [e for e in edges if e.get("type") in allowed_t]

        edges = sorted(edges, key=lambda e: (e["type"], e["source"], e["target"]))
        return edges[:limit]

    def _summarize_node(self, node_id: str) -> dict:
        sym = self.symbols_by_id.get(node_id)
        if sym is not None:
            return {
                "id": node_id,
                "kind": sym.kind,
                "display_name": sym.display_name,
                "document": sym.document,
            }
        if node_id.startswith("http_entrypoint:"):
            parts = node_id.split(":", 3)
            return {
                "id": node_id,
                "kind": "http_entrypoint",
                "document": parts[1] if len(parts) > 1 else "",
                "display_name": parts[2] if len(parts) > 2 else node_id,
            }
        if node_id.startswith("reactorstage:"):
            return {
                "id": node_id,
                "kind": "reactive_stage",
                "display_name": node_id,
                "document": "",
            }
        if node_id.startswith("springbean:"):
            return {
                "id": node_id,
                "kind": "spring_bean",
                "display_name": node_id,
                "document": "",
            }
        if node_id.startswith("netty:"):
            return {
                "id": node_id,
                "kind": "netty_component",
                "display_name": node_id,
                "document": "",
            }
        return {"id": node_id, "kind": "unknown", "display_name": node_id, "document": ""}

    def _class_symbol_for_method(self, method_symbol: str) -> str | None:
        method = self.symbols_by_id.get(method_symbol)
        if method is None:
            return None
        classes = [s for s in self.symbols_by_document.get(method.document, []) if s.kind == "Class"]
        return classes[0].symbol if classes else None

    def _field_injections_for_class(self, class_symbol: str) -> list[dict]:
        class_node = self.symbols_by_id.get(class_symbol)
        if class_node is None:
            return []
        fields = [
            s
            for s in self.symbols_by_document.get(class_node.document, [])
            if s.kind == "Field" and self.get_semantic_edges(s.symbol, direction="out", type_filter=["spring.injects"])
        ]
        out = []
        for field in fields:
            edges = self.get_semantic_edges(field.symbol, direction="out", type_filter=["spring.injects"], limit=100)
            out.append(
                {
                    "field": self._summarize_node(field.symbol),
                    "injects": edges,
                }
            )
        return out

    def _reactor_chain(self, return_stage: str) -> list[dict]:
        seen: set[str] = set()
        queue = [return_stage]
        stages: dict[str, dict] = {}
        allowed = {"reactor.operator_applies", "reactor.flows_to", "reactor.error_fallback_to"}

        while queue:
            node = queue.pop(0)
            if node in seen:
                continue
            seen.add(node)
            for edge in self.get_semantic_edges(node, direction="out", type_filter=list(allowed), limit=500):
                target = edge["target"]
                metadata = edge.get("metadata", {})
                if target.startswith("reactorstage:"):
                    stages[target] = {
                        "node": self._summarize_node(target),
                        "via": edge["type"],
                        "operator": metadata.get("operator", ""),
                        "range": metadata.get("range", []),
                    }
                    if target not in seen:
                        queue.append(target)

        def sort_key(item: dict) -> tuple:
            rng = item.get("range") or []
            return (rng[0], rng[1]) if len(rng) >= 2 else (999999, 999999)

        return sorted(stages.values(), key=sort_key)

    def get_mixed_flow(self, method_symbol: str) -> dict:
        return get_mixed_flow_with_store(self, method_symbol)

    def _neighbors(self, symbol_id: str) -> list[str]:
        return sorted(self.calls_out_by_symbol.get(symbol_id, set()))

    def trace_semantic_path(self, start_symbol: str, max_depth: int = 2, limit: int = 25) -> list[list[dict]]:
        if max_depth < 1:
            return []

        paths: list[list[str]] = []
        queue: list[tuple[str, list[str], int]] = [(start_symbol, [start_symbol], 0)]
        visited_prefixes: set[tuple[str, ...]] = set()

        while queue and len(paths) < limit:
            current, path, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for nxt in self._neighbors(current):
                if nxt in path:
                    continue
                new_path = path + [nxt]
                prefix = tuple(new_path)
                if prefix in visited_prefixes:
                    continue
                visited_prefixes.add(prefix)
                paths.append(new_path)
                queue.append((nxt, new_path, depth + 1))
                if len(paths) >= limit:
                    break

        def path_to_payload(symbol_path: list[str]) -> list[dict]:
            out: list[dict] = []
            for symbol in symbol_path:
                sym = self.symbols_by_id.get(symbol)
                if sym is None:
                    out.append({"symbol": symbol, "display_name": "", "document": ""})
                else:
                    out.append(
                        {
                            "symbol": sym.symbol,
                            "display_name": sym.display_name,
                            "document": sym.document,
                            "kind": sym.kind,
                        }
                    )
            return out

        return [path_to_payload(p) for p in paths]

    def _has_operator(self, return_stage: str, operator_name: str) -> bool:
        seen: set[str] = set()
        queue = [return_stage]
        allowed_types = {"reactor.operator_applies", "reactor.flows_to", "reactor.error_fallback_to"}

        while queue:
            node = queue.pop(0)
            if node in seen:
                continue
            seen.add(node)

            edges = self.get_semantic_edges(node, direction="out", type_filter=list(allowed_types), limit=500)
            for edge in edges:
                if edge.get("metadata", {}).get("operator") == operator_name:
                    return True
                target = edge.get("target")
                if target and target not in seen:
                    queue.append(target)

        return False

    def validate_fixture(self, fixture_id: str) -> dict:
        return validate_fixture_with_store(self, fixture_id)
