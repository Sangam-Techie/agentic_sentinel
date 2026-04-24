# Agentic Sentinel

> An autonomous API security testing agent — built with Python, httpx,
> Playwright, Ollama (local LLMs), LangGraph, and FastAPI.
> Designed for bug bounty automation and professional API security audits.

[![CI](https://github.com/Sangam-Techie/agentic_sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Sangam-Techie/agentic_sentinel/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Sangam-Techie/agentic_sentinel/branch/main/graph/badge.svg)](https://codecov.io/gh/Sangam-Techie/agentic_sentinel)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What This Is

Agentic Sentinel is a progressive build of a production-grade autonomous
API security agent, evolving from a governance-first foundation to a
complete multi-agent bug bounty and audit platform. It combines:

- **Autonomous agent loop** (perceive → reason → act → observe) with
  mandatory Human-In-The-Loop (HITL) governance for any MEDIUM+ risk action
- **API attack coverage**: BOLA/IDOR, JWT attacks, OAuth2 flaws,
  mass assignment, stateful multi-step authorization bypass
- **Shadow API discovery**: Playwright CDP listener captures
  JavaScript-rendered endpoints invisible to static scanners
- **Traffic interception**: mitmproxy addon feeds mid-flight request/response
  data into the agent's perception pipeline
- **LLM-powered reasoning**: Router/Reasoner pattern (Phi-3 routes,
  Mistral 7B reasons) — fully local via Ollama, zero cloud dependency
- **RAG-augmented analysis**: ChromaDB vector store with embedded OWASP
  API Top 10 context and OpenAPI spec chunks
- **Multi-agent coordination**: LangGraph StateGraph with specialist
  ReconAgent, AttackAgent, VerifyAgent, and ReportAgent
- **Adversarial self-validation**: RedTeamAgent vs BlueTeamAgent loop
  proves detection coverage before submission
- **Full audit trail**: Every proposed and confirmed finding — approved
  or blocked — written to SQLite with operator identity, risk level,
  and approval reason

Every offensive capability is HITL-gated. The agent proposes; the
human approves. Autonomous destructive action is architecturally impossible.

---

## Why This Tool, Not Burp Suite Pro

| Capability                                  | Burp Suite Pro            | Agentic Sentinel                                    |
| :------------------------------------------ | :------------------------ | :-------------------------------------------------- |
| Shadow API discovery (JS-rendered endpoints)| Manual, browser-dependent | Automated via Playwright CDP                        |
| Stateful multi-step BOLA sequences          | Manual                    | Automated, two-session management                   |
| LLM-reasoned endpoint prioritization        | ❌                        | Router/Reasoner — auditable chain                   |
| LLM hot-swap (change models in config)      | ❌                        | MCP standardization                                 |
| Full audit trail per finding                | Partial                   | Every action, every approval, SQLite                |
| Offline operation, zero cloud dependency    | Partial                   | 100% local — Ollama + ChromaDB with Cloud supported |
| Red vs Blue adversarial self-validation     | ❌                        | Built-in                                            |

## Project Status

Built epoch-by-epoch. Each epoch ends with a real competition run against
Hacker101 CTF or HackerOne targets. The gap list from each run defines
what the next epoch builds.

| Epoch | Theme | Key Capabilities | Status |
| :---  | :----------------------------------| :------------------------------------------------- | :------------ |
| **0** | **Foundations**                    | AgentBase, HITL governance, AuditLog, CI/CD        | ✅ Complete   |
| **1** | **Minimum Viable Competing Agent** | HTTPProber, BOLADetector, TokenBucket, CrudeReason | 🔄 In Progress|
| **2** | **Perception Deepening**           | mitmproxy, Playwright CDP, shadow APIs, JWT/OAuth2 | ⏳ Upcoming   |
| **3** | **Reasoning Deepening**            | MCP server, Router/Reasoner, ChromaDB RAG          |  ⏳ Upcoming  |
| **4** | **Scale and Architecture**         | LangGraph multi-agent, adversarial loop, dashboard | ⏳ Upcoming   |

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
**Lab targets** (containerized — no real systems required):

```bash
# Start vulnerable API targets
podman-compose --profile labs up -d

# Targets:
#   vulnerable_api  → localhost:9090
#   crAPI           → localhost:9091
#   Juice Shop      → localhost:9092
```

---

## Architecture
```
agentic_sentinel/
├── agents/
│   ├── base.py          AgentBase abstract class + DemoAgent
│   ├── types.py         Perception, AgentDecision, ActionResult
│   ├── audit.py         AgentRun / AgentAction SQLModel schema + AuditLog
│   ├── hitl.py          PermissionNode — HITL governance gate
│   ├── crude_reason.py  Single Ollama call (Epoch 1 — replaced in Epoch 3)
│   └── api_security_graph.py  LangGraph multi-agent pipeline (Epoch 4)
├── tools/
│   ├── http_prober.py         HTTPProber — async HTTP perception
│   ├── bola_detector.py       BOLADetector — HITL-gated IDOR enumeration
│   ├── openapi_parser.py      OpenAPI spec → structured APIMap
│   ├── playwright_agent.py    CDP network listener — shadow API discovery
│   ├── interceptor.py         mitmproxy addon — mid-flight interception
│   ├── stateful_prober.py     Multi-step BOLA sequences
│   ├── auth_prober.py         JWT + OAuth2 testing
│   └── mass_assignment_detector.py
├── utils/
│   └── rate_limiter.py        TokenBucket — async rate limiting (2 req/sec)
├── llm/
│   ├── router.py              RouterLLM — Phi-3, fast task classification
│   ├── reasoner.py            ReasoningLLM — Mistral 7B, OWASP-informed
│   ├── backend.py             LLMBackend abstract — hot-swap via config
│   └── structured_output.py   Pydantic output parsing + retry logic
├── rag/
│   └── api_knowledge_store.py ChromaDB — OpenAPI + OWASP embeddings
├── mcp_server.py              All tools exposed as MCP callables
└── config.py                  Centralised settings via environment variables
```

See [`architecture_decision_records/`](architecture_decision_records/) for
design rationale.

---

## Key Design Principles

**HITL Governance:** Every MEDIUM/HIGH/CRITICAL agent action requires
a human operator to type a one-time approval token before the action
executes. Kill switch (`AGENT_KILL_SWITCH=true`) halts all actions
immediately.

**Proposed vs Confirmed:** Every LLM finding is logged as
`proposed: true` until a deterministic verification script independently
confirms it. Only confirmed findings appear in reports. LLM hallucinations
cannot produce false submissions.

**Audit Trail:** Every action — approved, denied, or killed — is written
to an `AgentAction` row in SQLite, linked to a parent `AgentRun` row
that records operator identity and authorization reference.

**Authorization-to-Test First:** Active scanning modules will not run
without a completed `authorization_to_test.md` on file. Legal compliance
is a first-class feature, not an afterthought.

**Offline-First:** All lab work runs against local containers. All LLM
inference runs locally via Ollama. No external internet dependency for
any core capability.

**MCP Standardization:** All tools are exposed as MCP (Model Context
Protocol) callables. Swapping from Mistral to any other LLM requires
one config line change — zero glue code rewritten.

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

## Portfolio Artifacts (built epoch by epoch)

| Artifact | Epoch | Status |
| :--- | :--- | :--- |
| ADR-001: Agent Architecture | 0 | ✅ |
| ADR-002: Epoch 1 Tool Architecture | 1 | ⏳ |
| `reports/portfolio_artifact_001.md` (Hacker101 Postbook run) | 1 | ⏳ |
| ADR-003: Epoch 2 Perception Expansion | 2 | ⏳ |
| `reports/report_01_bola.md` (CVSS scored) | 4 | ⏳ |
| `reports/report_02_auth_bypass.md` (CVSS scored) | 4 | ⏳ |
| `reports/report_03_epoch4_full_pipeline.md` | 4 | ⏳ |
| Demo video (5–10 min end-to-end pipeline) | 4 | ⏳ |
| Sanitised `agent_audit_log.jsonl` from capstone run | 4 | ⏳ |
