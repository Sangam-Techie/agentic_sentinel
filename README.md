# Agentic Sentinel

> An AI-powered security pipeline for autonomous IoT/OT red team
> and blue team operations — built with Python, FastAPI, LangGraph,
> and Streamlit.

[![CI](https://github.com/Sangam-Techie/agentic_sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Sangam-Techie/agentic_sentinel/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Sangam-Techie/agentic_sentinel/branch/main/graph/badge.svg)](https://codecov.io/gh/Sangam-Techie/agentic_sentinel)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What This Is

Agentic Sentinel is a progressive build of a production-grade agentic security tool, evolving from a foundational skeleton to a complete security orchestration platform. It combines:

- **Autonomous agent loop** (perceive → reason → act → observe) with
  mandatory Human-In-The-Loop governance for any MEDIUM+ risk action
- **IoT/OT protocol coverage**: ONVIF, RTSP, MQTT, Modbus TCP, OPC-UA,
  BACnet, BLE, SNMP, CoAP, and more
- **Firmware analysis pipeline**: automated extraction, hardcoded
  credential scanning, CVE matching
- **RAG-powered threat intelligence**: ChromaDB vector store + offline
  CVE embeddings for context-aware analysis
- **Streamlit dashboard**: real-time agent run status, audit log viewer,
  risk heatmap
- **Full audit trail**: every agent action (approved or blocked) written
  to SQLite with operator identity, risk level, and approval reason

Every offensive capability is HITL-gated. The agent proposes; the human
approves. Autonomous destructive action is architecturally impossible.

---

## Project Status
This project is organized into logical milestones. Rather than adhering to a rigid timeline, each phase focuses on mastering specific domains of AI-driven security.

| Phase | Theme | Focus Areas | Status |
| :--- | :--- | :--- | :--- |
| **I** | **Foundations** | Env hardening, Async Agent Loop, HITL, CI/CD | ✅ Complete |
| **II** | **IoT/OT Edge** | Asset discovery, Camera bootstrap, Landscape mapping | 🔄 In progress |
| **III** | **Protocol Mastery** | Micro-modules for MQTT, Modbus, and ONVIF | ⏳ Upcoming |
| **IV** | **Deep Analysis** | Firmware analysis & vulnerability identification | ⏳ Upcoming |
| **V** | **Offensive Ops** | Multi-agent Red Team pipelines (LangGraph) | ⏳ Upcoming |
| **VI** | **Defensive Ops** | IDS/IPS integration, RAG-driven threat intelligence | ⏳ Upcoming |
| **VII** | **Capstone** | Dashboard, DevSecOps hardening, Production deployment | ⏳ Upcoming |

---

## Quick Start
```bash
# Clone and set up
git clone https://github.com/Sangam-Techie/agentic-sentinel.git
cd agentic-sentinel

# Create and activate virtual environment (linux)
python3 -m venv .venv && source .venv/bin/activate

# Install package and dev dependencies
uv pip install -e ".[dev]" #(uv prefered and recomended)

# Verify environment
python -m agentic_sentinel.environment_check

# Run the test suite
pytest --asyncio-mode=auto -v

# Run the demo agent (3 iterations, audit trail written to demo_audit.sqlite)
python -m agentic_sentinel.agents.base
```

---

## Architecture
```
agentic_sentinel/
├── agents/
│   ├── base.py      AgentBase abstract class + DemoAgent
│   ├── types.py     Perception, AgentDecision, ActionResult
│   ├── audit.py     AgentRun / AgentAction SQLModel schema + AuditLog
│   └── hitl.py      PermissionNode — HITL governance gate
├── tools/           Scanner, firmware analyser, credential auditor
├── protocols/       Per-protocol probe modules
├── compliance/      Pluggable compliance adapters: SIRA, IEC-62443
└── config.py        Centralised settings via environment variables
```

See [`architecture_decision_records/`](architecture_decision_records/) for
design rationale.

---

## Key Design Principles

**HITL Governance:** Every MEDIUM/HIGH/CRITICAL agent action requires
a human operator to type a one-time approval token before the action
executes. Kill switch (`AGENT_KILL_SWITCH=true`) halts all action
immediately.

**Audit Trail:** Every action — approved, denied, or killed — is written
to an `AgentAction` row in SQLite, linked to a parent `AgentRun` row
that records operator identity and authorization reference.

**Authorization-to-Test First:** Active scanning modules will not run
without a completed `authorization_to_test.md` on file. Legal compliance
is a first-class feature, not an afterthought.

**Offline-First:** All lab work runs against local containers. No
external internet dependency for any exercise.

---

## Legal & Ethics

This tool is built for **authorised security testing only**.
Running active scans or exploit simulations against systems you do not
own or have explicit written permission to test is illegal in most
jurisdictions. Every active-scan module requires a signed
Authorization-to-Test (ATT) form before proceeding.

See [`authorization_to_test.md`](authorization_to_test.md) for the
template.

---

## Development
```bash
# Run linter
ruff check .

# Run type checker
mypy agentic_sentinel/ --ignore-missing-imports

# Run tests with coverage
pytest --asyncio-mode=auto --cov=agentic_sentinel --cov-report=term-missing

# Build container images locally
podman build -t agentic-sentinel-backend  -f backend/Dockerfile  .
podman build -t agentic-sentinel-dashboard -f dashboard/Dockerfile .
```

---

## Portfolio Artifacts

Upon completion of the final milestone, this repository should contain:

1. Complete GitHub repo with CI badges and architecture diagram
2. Three incident-style case study reports
3. Demo video (5–10 min end-to-end pipeline demonstration)
4. Sanitised `agent_audit_log.sqlite` from the capstone run
5. Architecture Decision Records: ADR-001 through ADR-003 minimum
