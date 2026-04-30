"""
Tests for AuditLog - database operations.
Uses an in-memory SQLite DB so no files are created during CI.
"""

import pytest

from agentic_sentinel.agents.audit import AgentAction, AuditLog


@pytest.fixture
def log():
    """In-memory audit log - no files created during tests."""
    return AuditLog(db_url="sqlite:///:memory:", jsonl_path=":memory-jsonl:")

def test_record_returns_action_with_id(log):
    action = log.record(AgentAction(
        run_id="test-001",
        tool="TestTool",
        target="/api/test",
        risk_level="LOW",
        result_summary="test",
        authorization_ref="ATT-00",
    ))
    assert action.id is not None

def test_proposed_finding_appears_in_get_proposed(log):
    log.record(AgentAction(
        run_id="test-001",
        tool="BOLADetector",
        target="/api/v1/orders/{id}",
        risk_level="HIGH",
        result_summary="200 OK - different user data",
        authorization_ref="ATT-001",
        proposed=True,
        confirmed=False,
    ))
    proposed = log.get_proposed("test-001")
    assert len(proposed) == 1
    assert proposed[0].tool == "BOLADetector"

def test_mark_confirmed_promotes_finding(log):
    action = log.record(AgentAction(
        run_id="test-001",
        tool="BOLADetector",
        target="/api/v1/orders{id}",
        risk_level="HIGH",
        result_summary="200 OK - different user data",
        authorization_ref="ATT-001",
        proposed=True,
        confirmed=False,
    ))
    confirmed = log.mark_confirmed(action.id)
    assert confirmed.confirmed is True
    assert len(log.get_confirmed("test-001")) == 1
    assert len(log.get_proposed("test-001")) == 0

def test_mark_confirmed_returns_none_for_missing_id(log):
    result = log.mark_confirmed(9999)
    assert result is None

def test_run_summary_counts_correctly(log):
    # One governance row (not proposed, not confirmed)
    log.record(AgentAction(
        run_id="test-001", tool="PermissionNode", target="/api/test",
        risk_level="LOW", result_summary="approved",
        authorization_ref="ATT-000", proposed=False, confirmed=False,
    ))
    # One proposed finding
    action = log.record(AgentAction(
        run_id="test-001", tool="BOLADetector", target="/api/v1/orders/{id}",
        risk_level="HIGH", result_summary="potential BOLA",
        authorization_ref="ATT-001", proposed=True, confirmed=False,
    ))
    # Promote it
    log.mark_confirmed(action.id)

    summary = log.run_summary("test-001")
    assert summary["total_actions"] == 2
    assert summary["confirmed_findings"] == 1
    assert summary["proposed_findings"] == 0

def test_kill_switch_blocks_all_risk_levels():
    import os

    from agentic_sentinel.agents.hitl import PermissionNode
    log = AuditLog(db_url="sqlite:///:memory:", jsonl_path=":memory-jsonl:")
    node = PermissionNode(audit_log=log, run_id="test")
    os.environ["AGENT_KILL_SWITCH"] = "true"
    try:
        for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            result = node.request_permission(
                "TestTool", "/api/test", level, "test", "ATT-000"
            )
            assert result is False, f"Kill switch failed to block {level}"
    finally:
        os.environ["AGENT_KILL_SWITCH"] = "false"

def test_agentbase_enforces_abstract_methods():
    from agentic_sentinel.agents.base import AgentBase

    class IncompleteAgent(AgentBase):
        async def perceive(self): pass
        async def reason(self, p): pass
        # act and observe deliberately not implemented

    with pytest.raises(TypeError):
        IncompleteAgent(audit_log=None, run_id="x")
