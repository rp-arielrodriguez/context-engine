from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "context-engine"
PACKAGE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(
    os.environ.get(
        "CONTEXT_ENGINE_CONFIG_DIR",
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME,
    )
).expanduser()
CACHE_DIR = Path(
    os.environ.get(
        "CONTEXT_ENGINE_CACHE_DIR",
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_NAME,
    )
).expanduser()
TOOLS_DIR = PACKAGE_DIR / "adapters" / "scip"
EXPORTER_SRC = TOOLS_DIR / "ScipJsonExporter.java"
EXPORTER_CLASSES = CACHE_DIR / "java-classes"
STORE_CACHE_DIR = CACHE_DIR / "store-cache"

SCIP_JAVA_PROTO_JAR = Path(
    os.environ.get(
        "SCIP_JAVA_PROTO_JAR",
        "~/Library/Caches/Coursier/v1/https/repo1.maven.org/maven2/"
        "com/sourcegraph/scip-java-proto/0.12.3/scip-java-proto-0.12.3.jar",
    )
).expanduser()

PROTOBUF_JAVA_JAR = Path(
    os.environ.get(
        "PROTOBUF_JAVA_JAR",
        "~/Library/Caches/Coursier/v1/https/repo1.maven.org/maven2/"
        "com/google/protobuf/protobuf-java/3.15.6/protobuf-java-3.15.6.jar",
    )
).expanduser()
