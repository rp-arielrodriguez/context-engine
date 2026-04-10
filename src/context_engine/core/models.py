from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentRecord:
    path: str
    language: str
    symbols_count: int
    occurrences_count: int


@dataclass(frozen=True)
class SymbolRecord:
    symbol: str
    display_name: str
    enclosing_symbol: str
    kind: str
    document: str


@dataclass(frozen=True)
class OccurrenceRecord:
    symbol: str
    display_name: str
    enclosing_symbol: str
    kind: str
    document: str
    range: tuple[int, ...]
    enclosing_range: tuple[int, ...]
    symbol_roles: int
    is_definition: bool
    is_import: bool
    is_write: bool
    is_read: bool
    is_generated: bool
    is_test: bool
    is_forward_definition: bool


@dataclass(frozen=True)
class IndexMetadata:
    project_root: str
    tool_name: str
    tool_version: str
    documents_count: int
    external_symbols_count: int
