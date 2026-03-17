# ADR-001 — Agent Architecture, Project Layout and CI/CD

**Date:** 2026-03-13
**Status:** Accepted
**Authors:** Sangam Aryal

---

## Context

This project requires a codebase that is simultaneously:

1. **A learning journal** — code is introduced incrementally across planned development phases, with skeleton files and scratch work at each stage.
2. **A professional portfolio artifact** — by the final milestone, the codebase must be employer-ready: clean imports, hardened CI/CD, tested, and documented.

These two requirements are in tension. A rigid time-based folder layout (week_01/day_02/) satisfies (1) but breaks (2) by forcing sys.path manipulation in every file that imports from another day's work. This
pattern breaks CI pipelines (working directory differs from developer
machine) Furthermore, a strict week based deadline does not account for the high technical overhead of mastering environment hardening (Fedora/SSH/CI-CD) and deep-dive theory.

An installable package layout satisfies (2) but risks losing (1): if
scratch work goes directly into the package, the git history becomes
a mixture of exploratory code and production code with no clear separation.

---

## Decision

**Split the repository into two zones with a hard boundary:**

### Zone 1: `agentic_sentinel/` — Production Package

All code that is imported by other modules, run in CI, or shipped in a container image lives here. Development follows a 70/30 split: 70% original main logic authored manually for deep comprehension, and 30% skeleton/boilerplate sourced from reference materials.
```
agentic_sentinel/
  __init__.py
  agents/
    __init__.py      ← clean re-exports of public API
    base.py          ← AgentBase, DemoAgent
    types.py         ← Perception, AgentDecision, ActionResult
    audit.py         ← AgentRun, AgentAction, AuditLog
    hitl.py          ← PermissionNode
  tools/             ← scanner, firmware analyser, etc.
  protocols/         ← MQTT, Modbus, ONVIF, etc.
  compliance/        ← pluggable compliance adapters
  config.py          ← shared settings via environment variables
```

Installed in editable mode via `pip install -e ".[dev]"` so all imports
resolve to `from agentic_sentinel.X import Y` with no path hacks.

### Zone 2: `journal/` — Learning Scratch Work

Skeleton files, notes, and exploratory code live here before they are
integrated into the package. Files in `journal/` are never imported by
production code. They exist for the learning record only.
```
journal/
  phase_01_foundations/
    01_env_and_ssh_hardening.md
    02 retrospective.md
    03_scratch_agent_loop.py     ← the original 70/30 skeleton
  phase_02_iot_edge/
    ...
```

### Keystone: `pyproject.toml`

A single `pyproject.toml` at the project root:
- Declares `agentic_sentinel` as an installable package
- Lists runtime and dev dependencies
- Configures ruff, mypy, and pytest
- Defines CLI entry points (added as the project grows)

This makes `pip install -e ".[dev]"` the single setup command for any
environment: local dev, CI runner, container build.

Milestone-Based Velocity:
I have moved away from a strict 12-week calendar to a Phase-based roadmap. This allows for "Deep-Dive" cycles into infrastructure (Fedora hardening, CI/CD, Git internals) and other necessary suppliments without the pressure of artificial weekly deadlines.

The 70/30 Authorship Rule:
To ensure maximum architectural retention, 70% of core logic is authored manually, while 30% utilizes skeletons for boilerplate. This prevents "LLM-dependency" and ensures the developer can defend every line of code in a technical interview.

---

## Consequences

### Positive

- `from agentic_sentinel.agents import AgentBase` works everywhere:
  local machine, CI runner, Docker/Podman container, pytest, Streamlit,
  FastAPI — with no `sys.path` manipulation anywhere.
- CI (`pip install -e ".[dev]"`) is identical to local dev setup.
  "Works on my machine" failures are structurally prevented.
- `agentic_sentinel/__init__.py` sub-package `__init__.py` files expose
  a stable public API. Internal reorganisation doesn't break callers.
- The `journal/` separation makes it clear what is production code and
  what is learning material — important for a portfolio reviewer.

### Negative / Trade-offs

- Overhead: Moving from "Weekly" to "Phases" requires frequent README   and roadmap updates to keep the portfolio story coherent.
- `pip install -e .` must be re-run if `pyproject.toml` changes
  (new dependencies, new entry points). This is rare but easy to forget.
- The flat package layout (no `src/` directory) means accidental imports
  from the project root are theoretically possible. Mitigated by always
  running pytest from the repo root with `pytest tests/` rather than
  `python -m pytest` from inside a subdir.
-  Git Complexity: Maintaining a professional commit history occasionally requires complex operations (rebases/resets) when feature commits are missed during rapid iteration.

### Neutral

- The `journal/` folder is gitignored for `*.pyc` and `__pycache__` but
  tracked for `.py` and `.md` files. Learning notes are part of the
  portfolio story.

---

## Alternatives Considered

**Week/day folder layout as Python modules**
Rejected. Requires `sys.path` hacking in every file. Breaks CI.
Described in Context above. And creates "calendar debt" where falling behind a week feels like failure rather than deep learning.


**`src/` layout**
Considered. The `src/` layout adds a level of indirection
(`src/agentic_sentinel/` instead of `agentic_sentinel/`) that prevents
accidental imports from the project root. Rejected in favour of the
flat layout because: (a) the flat layout is what most major Python
projects use; (b) the `pyproject.toml` editable install already enforces
correct import resolution; (c) the extra directory level adds friction
without meaningful benefit for a single-developer project.

**Separate repos per week**
Rejected. Prevents building a coherent capstone artifact. Portfolio
value comes from a single repo with a clean end-to-end story.

---

## Review Trigger

Revisit this ADR if:
- A second developer joins the project (team conventions may differ)
- The project needs to publish to PyPI (would require src/ layout or
  explicit package discovery configuration)
- A protocol module needs to live outside `agentic_sentinel/` for
  licensing reasons
- The learning velocity significantly deviates from the phased roadmap.


**CI: uv in GitHub Actions uses --system**
Context: GitHub runners don’t activate a venv by default; uv pip install ... fails with “No virtual environment found”.

Decision: Use uv pip install --system ... in CI jobs (lint + tests) to install into runner Python.

Consequences:
Positive: simpler, fewer moving parts, fixes CI deterministically.

Trade-off: less isolation than a venv; acceptable in ephemeral CI runners.

Alternatives:
Create .venv with uv venv and add PATH/VIRTUAL_ENV in each step.

**Supply chain artifacts: SBOM + vuln scanning with Podman**
Context: Podman-built images aren’t reliably visible to scanners expecting Docker daemon / Podman socket in GitHub Actions.

Decision:
SBOM: syft dir:backend (filesystem SBOM) for now.
Vuln scanning: podman save backend/dashboard image -o image.tar + Trivy scan using input: image.tar.

Consequences:
Positive: avoids daemon/socket issues; scans the actual image (Trivy tarball) while staying Podman-first.
Trade-off: SBOM is filesystem-based (not image-layer SBOM) until you switch SBOM to docker-archive: from the tarball later.

Future trigger:
When publishing images/hardening: generate SBOM from the image tarball (syft docker-archive:...) and/or scan images from a registry ref.
