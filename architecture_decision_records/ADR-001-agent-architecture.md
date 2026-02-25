# ADR-001 — Agent Architecture

## Status
Accepted (revised Day 1 refactor)

## Context
Initial scaffold used week/day folders as Python modules, requiring
sys.path manipulation for cross-module imports. This pattern breaks
CI pipelines and makes onboarding painful.

## Decision
All production code lives in the `agentic_sentinel/` installable package.
`pyproject.toml` with `pip install -e .` provides clean import paths
everywhere. Week/day folders are retained in `journal/` as a learning
scratchpad only.

## Package Structure
agentic_sentinel/
  agents/     — agent loop, HITL governance, audit trail
  tools/      — reusable tool registry
  protocols/  — per-protocol probe modules (later weeks)
  compliance/ — pluggable compliance adapters (later week)
  config.py   — shared settings

## Consequences
- All imports use `from agentic_sentinel.X import Y` — no exceptions
- New modules go in the appropriate sub-package before being used
- `__init__.py` re-exports maintain a stable public API surface
- CI installs via `pip install -e ".[dev]"` — no requirements.txt fragility
