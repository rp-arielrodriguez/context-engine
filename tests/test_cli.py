from __future__ import annotations

import subprocess
import sys

from context_engine.surfaces.cli.main import build_parser


def test_cli_parser_prog_name() -> None:
    parser = build_parser()
    assert parser.prog == "context-engine"


def test_cli_help_lists_commands() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "context_engine.surfaces.cli.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "find-symbols" in proc.stdout
    assert "get-mixed-flow" in proc.stdout
