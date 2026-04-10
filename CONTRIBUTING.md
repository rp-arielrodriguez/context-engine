# Contributing

## Scope

This project is building a local-first semantic engine on top of SCIP with first-class framework semantics for Spring, Reactor/WebFlux, and Netty.

Please keep contributions aligned with that goal. Small, focused pull requests are preferred.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Running Checks

Run tests:

```bash
pytest
```

Run a CLI smoke check against a real SCIP index:

```bash
context-engine --index "/path/to/index.scip" validate-fixture --fixture-id "shoppingcart-http-main"
```

Run the MCP measurement script:

```bash
./scripts/measure-mcp.sh /path/to/index.scip
```

## Design Rules

- Preserve the `core/ -> app/ -> surfaces/` and `adapters/ -> core` boundary rules documented in `docs/architecture.md`.
- Prefer the smallest correct change.
- Do not add broad abstractions before they are needed.
- Keep `core/` language-agnostic in design even if the implementation is currently Python.
- Treat Spring, Reactor, and Netty semantics as first-class concerns, not optional enrichments.

## Pull Requests

- Explain the behavior change and why it is needed.
- Include tests for non-trivial behavior changes.
- Update docs when user-facing behavior or setup changes.
- Avoid mixing refactors with behavior changes unless there is a clear reason.

## Reporting Issues

When filing a bug, include:

- the command you ran
- the SCIP index source
- the expected behavior
- the observed behavior
- any stderr or traceback output
