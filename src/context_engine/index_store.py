from __future__ import annotations

from pathlib import Path

from .app.fixture_service import validate_fixture as validate_fixture_with_store
from .app.mixed_flow_service import get_mixed_flow as get_mixed_flow_with_store
from .app.query_api import (
    find_documents as find_documents_with_store,
    find_symbols as find_symbols_with_store,
    get_occurrences as get_occurrences_with_store,
    get_references as get_references_with_store,
    get_semantic_edges as get_semantic_edges_with_store,
    get_symbol as get_symbol_with_store,
    trace_semantic_path as trace_semantic_path_with_store,
)
from .app.store_helpers import definitions_by_document, infer_caller_by_position
from .adapters.scip.loader import load_records_from_ndjson
from .adapters.scip.index_builder import build_call_graph, populate_store_indexes
from .adapters.runtime.source_reader import read_source
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
from .core.models import DocumentRecord, IndexMetadata, OccurrenceRecord, SymbolRecord


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

        populate_store_indexes(self)
        build_call_graph(self)
        spring_edges = self._build_spring_edges()
        reactor_edges = self._build_reactor_edges(spring_edges)
        netty_edges = self._build_netty_edges(spring_edges, reactor_edges)
        self.semantic_edges = spring_edges + reactor_edges + netty_edges
        self.semantic_edges_by_source: dict[str, list[dict]] = {}
        self.semantic_edges_by_target: dict[str, list[dict]] = {}
        for edge in self.semantic_edges:
            self.semantic_edges_by_source.setdefault(edge["source"], []).append(edge)
            self.semantic_edges_by_target.setdefault(edge["target"], []).append(edge)

    def _infer_caller_by_position(self, occurrence: OccurrenceRecord) -> str | None:
        return infer_caller_by_position(self, occurrence)

    def _definitions_by_document(self, document: str) -> dict[str, OccurrenceRecord]:
        return definitions_by_document(self, document)

    def _read_source(self, document: str) -> str:
        return read_source(self, document)

    def _build_spring_edges(self) -> list[dict]:
        return build_spring_edges(self)

    def _build_reactor_edges(self, spring_edges: list[dict]) -> list[dict]:
        return build_reactor_edges(self, spring_edges)

    def _build_netty_edges(self, spring_edges: list[dict], reactor_edges: list[dict]) -> list[dict]:
        return build_netty_edges(spring_edges, reactor_edges)

    @classmethod
    def from_ndjson(cls, ndjson_path: Path) -> "IndexStore":
        metadata, documents, symbols, occurrences = load_records_from_ndjson(ndjson_path, cls._normalize_symbol)
        return cls(metadata, documents, symbols, occurrences)

    def find_documents(self, query: str, limit: int = 20) -> list[dict]:
        return find_documents_with_store(self, query, limit=limit)

    def find_symbols(self, query: str, path_filter: str | None = None, limit: int = 20) -> list[dict]:
        return find_symbols_with_store(self, query, path_filter=path_filter, limit=limit)

    def get_symbol(self, symbol_id: str) -> dict:
        return get_symbol_with_store(self, symbol_id)

    def get_occurrences(self, symbol_id: str, path_filter: str | None = None, limit: int = 100) -> list[dict]:
        return get_occurrences_with_store(self, symbol_id, path_filter=path_filter, limit=limit)

    def get_references(self, symbol_id: str, path_filter: str | None = None, limit: int = 100) -> list[dict]:
        return get_references_with_store(self, symbol_id, path_filter=path_filter, limit=limit)

    def get_semantic_edges(
        self,
        node_id: str,
        direction: str = "both",
        provenance_filter: list[str] | None = None,
        type_filter: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return get_semantic_edges_with_store(
            self,
            node_id,
            direction=direction,
            provenance_filter=provenance_filter,
            type_filter=type_filter,
            limit=limit,
        )

    def get_mixed_flow(self, method_symbol: str) -> dict:
        return get_mixed_flow_with_store(self, method_symbol)

    def trace_semantic_path(self, start_symbol: str, max_depth: int = 2, limit: int = 25) -> list[list[dict]]:
        return trace_semantic_path_with_store(self, start_symbol, max_depth=max_depth, limit=limit)

    def validate_fixture(self, fixture_id: str) -> dict:
        return validate_fixture_with_store(self, fixture_id)
