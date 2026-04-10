from __future__ import annotations

import importlib

import context_engine.adapters.runtime.paths as runtime_paths


def test_config_dirs_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXT_ENGINE_CONFIG_DIR", "/tmp/context-engine-config-test")
    monkeypatch.setenv("CONTEXT_ENGINE_CACHE_DIR", "/tmp/context-engine-cache-test")
    reloaded = importlib.reload(runtime_paths)

    assert str(reloaded.CONFIG_DIR) == "/tmp/context-engine-config-test"
    assert str(reloaded.CACHE_DIR) == "/tmp/context-engine-cache-test"

    importlib.reload(runtime_paths)
