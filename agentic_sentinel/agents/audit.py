

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import Field, Session, SQLModel, create_engine, select


class AgentAction(SQLModel, table=True):
    # Primary key — database assigns this on INSERT, so it starts as None
    id: int|None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str = Field(index=True)
    tool: str
    target: str
    risk_level: str
    result_summary: str
    authorization_ref: str
    proposed: bool = Field(default=True)
    confirmed: bool = Field(default=False)

    tested_value: str = Field(default="")
    raw_request: str = Field(default="")
    raw_response: str = Field(default="")


class AuditLog:
    def __init__(
        self,
        db_url: str = "sqlite:///agent_audit.sqlite",
        jsonl_path: str = "audit.jsonl",
    ) -> None:
        self._engine = create_engine(connect_args={"check_same_thread": False}, url=db_url)
        SQLModel.metadata.create_all(self._engine)
        self._jsonl_path: Path|None = None if jsonl_path == ":memory-jsonl:" else Path(jsonl_path)

    def record(self, action: AgentAction) -> AgentAction:
        with Session(self._engine) as session:
            session.add(action)
            session.commit()
            session.refresh(action)
        if self._jsonl_path is not None:
            with self._jsonl_path.open("a", encoding="utf-8") as f:
                f.write(action.model_dump_json() + "\n")

        return action

    def get_proposed(self, run_id: str) -> list[AgentAction]:
        with Session(self._engine) as session:
            statement = (
                select(AgentAction)
                .where(AgentAction.run_id == run_id)
                .where(AgentAction.proposed == True) # noqa: E712
                .where(AgentAction.confirmed == False) # noqa: E712
            )
            return list(session.exec(statement).all())

    def get_confirmed(self, run_id: str) -> list[AgentAction]:
        with Session(self._engine) as session:
            statement = (
                select(AgentAction)
                .where(AgentAction.run_id == run_id)
                .where(AgentAction.confirmed == True) # noqa: E712
            )
            return list(session.exec(statement).all())

    def get_all_actions(self, run_id: str) -> list[AgentAction]:
        """Get all actions for a run_id, regardless of proposed/confirmed status."""
        with Session(self._engine) as session:
            statement = select(AgentAction).where(AgentAction.run_id == run_id)
            return list(session.exec(statement).all())

    def mark_confirmed(self, action_id: int) -> AgentAction|None:
        with Session(self._engine) as session:
            action = session.get(AgentAction, action_id)
            if action is None:
                return None
            action.confirmed = True
            session.add(action)
            session.commit()
            session.refresh(action)
            return action

    def tail_jsonl(self, n: int = 10) -> list[dict[str, str]]:
        if self._jsonl_path is None or not self._jsonl_path.exists():
            return []
        lines = self._jsonl_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines[-n:] if line.strip()]

    def export_jsonl_for_rag(self, run_id: str|None = None) -> list[dict[str, str]]:
        """
        Return all JSONL lines as dicts, optionally filtered by run_id.

        Used by Epoch 3's ChromaDB RAG store to ingest confirmed findings
        as documents. The RAG store calls this, embeds each dict's
        result_summary and target, and stores them for semantic retrieval.

        If run_id is None: return all lines from the entire JSONL file.
        If run_id is provided: return only lines matching that run.
        """
        if self._jsonl_path is None or not self._jsonl_path.exists():
            return []
        all_lines = [
            json.loads(line)
            for line in self._jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if run_id is None:
            return all_lines
        return [row for row in all_lines if row.get("run_id") == run_id]

    def run_summary(self, run_id: str) -> dict[str, Any]:
        with Session(self._engine) as session:
            all_actions = list(
                session.exec(
                    select(AgentAction).where(AgentAction.run_id == run_id)
                ).all()
            )
        total = len(all_actions)
        proposed = sum(1 for a in all_actions if a.proposed and not a.confirmed)
        confirmed = sum(1 for a in all_actions if a.confirmed)
        by_risk: dict[str, int] = {}
        for a in all_actions:
            by_risk[a.risk_level] = by_risk.get(a.risk_level, 0) + 1

        return {
            "run_id": run_id,
            "total_actions": total,
            "proposed_findings": proposed,
            "confirmed_findings": confirmed,
            "by_risk_level": by_risk,
        }

if __name__ == "__main__":
    import os

    TEST_DB = "smoke_test_audit.sqlite"
    TEST_JSONL = "smoke_test_audit.jsonl"

    # Clean up any previous test run
    for f in [TEST_DB, TEST_JSONL]:
        if os.path.exists(f):
            os.remove(f)

    log = AuditLog(db_url=f"sqlite:///{TEST_DB}", jsonl_path=TEST_JSONL)

    # 1. Write a governance action (PermissionNode auto-approve)
    log.record(AgentAction(
        run_id="smoke-001",
        tool="PermissionNode:DemoTool",
        target="/api/v1/demo",
        risk_level="LOW",
        result_summary="APPROVED — auto-approved: below HITL threshold",
        authorization_ref="ATT-000-DEMO",
        proposed=False,
        confirmed=False,
    ))

    # 2. Write a proposed BOLA finding
    bola_action = log.record(AgentAction(
        run_id="smoke-001",
        tool="BOLADetector",
        target="/api/v1/orders/{id}",
        risk_level="HIGH",
        result_summary="200 OK — different user's data returned",
        authorization_ref="ATT-001",
        tested_value="1043",
        raw_request="GET /api/v1/orders/1043 HTTP/1.1\nHost: localhost:9090",
        raw_response="HTTP/1.1 200 OK\n{\"order_id\": 1043, \"user_id\": 42}",
        proposed=True,
        confirmed=False,
    ))

    # 3. Promote the BOLA finding to confirmed (VerificationEngine would do this)
    assert bola_action.id is not None, "bola_action.id should not be None after record()"
    confirmed = log.mark_confirmed(bola_action.id)
    assert confirmed is not None and confirmed.confirmed is True, \
        "mark_confirmed() failed"

    # 4. Write an informational row
    log.record(AgentAction(
        run_id="smoke-001",
        tool="HTTPProber",
        target="/api/v1/health",
        risk_level="LOW",
        result_summary="200 OK — health check passed",
        authorization_ref="ATT-001",
        proposed=False,
        confirmed=False,
    ))

    # ── Verify reads ──────────────────────────────────────────────────────────
    jsonl_tail = log.tail_jsonl(n=3)
    assert len(jsonl_tail) == 3, f"Expected 3 JSONL lines, got {len(jsonl_tail)}"

    confirmed_findings = log.get_confirmed("smoke-001")
    assert len(confirmed_findings) == 1, \
        f"Expected 1 confirmed finding, got {len(confirmed_findings)}"
    assert confirmed_findings[0].tool == "BOLADetector"

    proposed_findings = log.get_proposed("smoke-001")
    assert len(proposed_findings) == 0, \
        "Proposed list should be empty after mark_confirmed()"

    summary = log.run_summary("smoke-001")
    assert summary["total_actions"] == 3
    assert summary["confirmed_findings"] == 1
    assert summary["proposed_findings"] == 0

    rag_export = log.export_jsonl_for_rag(run_id="smoke-001")
    assert len(rag_export) == 3, \
        f"RAG export should have 3 rows, got {len(rag_export)}"

    # ── Print results ─────────────────────────────────────────────────────────
    print("\nJSONL tail (last 3 entries):")
    for entry in jsonl_tail:
        print(f"  [{entry['risk_level']}] {entry['tool']} → {entry['result_summary']}")

    print(f"\nRun summary: {summary}")
    print(f"SQLite confirmed count: {len(confirmed_findings)}")
    print(f"RAG export row count: {len(rag_export)}")
    print("\n✅ AuditLog smoke test passed.")

    # Clean up
    for f in [TEST_DB, TEST_JSONL]:
        if os.path.exists(f):
            os.remove(f)
