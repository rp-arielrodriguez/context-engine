from __future__ import annotations

import json
from pathlib import Path

from ...core.models import DocumentRecord, IndexMetadata, OccurrenceRecord, SymbolRecord


def load_records_from_ndjson(ndjson_path: Path, normalize_symbol) -> tuple[IndexMetadata, list[DocumentRecord], list[SymbolRecord], list[OccurrenceRecord]]:
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
                symbol = normalize_symbol(row["symbol"], document)
                enclosing_raw = row.get("enclosing_symbol", "")
                enclosing_symbol = normalize_symbol(enclosing_raw, document) if enclosing_raw else ""
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
                symbol = normalize_symbol(row.get("symbol", ""), document)
                enclosing_raw = row.get("enclosing_symbol", "")
                enclosing_symbol = normalize_symbol(enclosing_raw, document) if enclosing_raw else ""
                occurrences.append(
                    OccurrenceRecord(
                        symbol=symbol,
                        display_name=row.get("display_name", ""),
                        enclosing_symbol=enclosing_symbol,
                        kind=row.get("kind", ""),
                        document=document,
                        range=tuple(int(x) for x in row.get("range", [])),
                        enclosing_range=tuple(int(x) for x in row.get("enclosing_range", [])),
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

    return metadata, documents, symbols, occurrences
