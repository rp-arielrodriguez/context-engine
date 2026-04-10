from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from ..runtime.paths import (
    CACHE_DIR,
    EXPORTER_CLASSES,
    EXPORTER_SRC,
    PROTOBUF_JAVA_JAR,
    SCIP_JAVA_PROTO_JAR,
)


class ExportError(RuntimeError):
    pass


def _classpath() -> str:
    return f"{SCIP_JAVA_PROTO_JAR}:{PROTOBUF_JAVA_JAR}"


def _ensure_dependencies() -> None:
    if not SCIP_JAVA_PROTO_JAR.exists():
        raise ExportError(f"Missing SCIP proto jar: {SCIP_JAVA_PROTO_JAR}")
    if not PROTOBUF_JAVA_JAR.exists():
        raise ExportError(f"Missing protobuf java jar: {PROTOBUF_JAVA_JAR}")
    if not EXPORTER_SRC.exists():
        raise ExportError(f"Missing exporter source: {EXPORTER_SRC}")


def _compile_exporter() -> None:
    EXPORTER_CLASSES.mkdir(parents=True, exist_ok=True)
    class_file = EXPORTER_CLASSES / "ScipJsonExporter.class"
    if class_file.exists() and class_file.stat().st_mtime_ns >= EXPORTER_SRC.stat().st_mtime_ns:
        return
    cmd = [
        "javac",
        "-cp",
        _classpath(),
        "-d",
        str(EXPORTER_CLASSES),
        str(EXPORTER_SRC),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ExportError(f"javac failed:\n{proc.stdout}\n{proc.stderr}")


def _cache_file(index_path: Path) -> Path:
    stat = index_path.stat()
    fingerprint = f"{index_path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}".encode("utf-8")
    digest = hashlib.sha256(fingerprint).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"scip-export-{digest}.ndjson"


def export_ndjson(index_path: Path, force: bool = False) -> Path:
    index_path = index_path.expanduser().resolve()
    if not index_path.exists():
        raise ExportError(f"Index not found: {index_path}")

    _ensure_dependencies()
    _compile_exporter()

    out_file = _cache_file(index_path)
    if out_file.exists() and not force:
        return out_file

    tmp_file = out_file.with_suffix(out_file.suffix + ".tmp")

    cmd = [
        "java",
        "-cp",
        f"{EXPORTER_CLASSES}:{_classpath()}",
        "ScipJsonExporter",
        str(index_path),
    ]

    with tmp_file.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, text=True)

    if proc.returncode != 0:
        if tmp_file.exists():
            tmp_file.unlink()
        raise ExportError(f"Exporter failed:\n{proc.stderr}")

    tmp_file.replace(out_file)

    return out_file
