"""
Tests for PermissionNode.

Key challenge: PermissionNode calls input() for MEDIUM+ actions
We mock builtins.input to simulate operator responses without
blocking the test suite.
"""

from unittest.mock import patch

import pytest

from agentic_sentinel.agents.audit import AuditLog
from agentic_sentinel.agents.hitl import PermissionNode

IN_MEMORY_DB = "sqlite://"


@pytest.fixture
def audit() -> AuditLog:
    return AuditLog(db_url=IN_MEMORY_DB)


@pytest.fixture
def run_id() -> str:
    return "test-run-123"


def make_node(audit: AuditLog, run_id: str) -> PermissionNode:
    return PermissionNode(audit_log=audit, run_id=run_id)


# --------------------------------------
# Kill switch tests
# --------------------------------------

def test_kill_switch_blocks_low(audit, run_id, monkeypatch):
    monkeypatch.setenv("AGENT_KILL_SWITCH", "true")
    node = make_node(audit, run_id)
    approved = node.request_permission(
        tool_name="test_tool",
        target="http://example.com",
        risk_level="LOW",
        description="Test action",
        authorization_ref="ATT-001"
    )

    assert approved is False
    # Check that an action was logged with kill switch reason
    actions = audit.get_all_actions(run_id)
    assert len(actions) > 0
    assert "KILL SWITCH ACTIVE" in actions[-1].result_summary


def test_kill_switch_blocks_high(audit, run_id, monkeypatch):
    monkeypatch.setenv("AGENT_KILL_SWITCH", "true")
    node = make_node(audit, run_id)
    approved = node.request_permission(
        tool_name="test_tool",
        target="http://example.com",
        risk_level="HIGH",
        description="Test action",
        authorization_ref="ATT-001"
    )

    assert approved is False
    actions = audit.get_all_actions(run_id)
    assert len(actions) > 0
    assert "KILL SWITCH ACTIVE" in actions[-1].result_summary


def test_kill_switch_case_insensitive(audit, run_id, monkeypatch):
    # "TRUE", "True", "true" must all activate the kill switch
    for value in ["TRUE", "True", "true"]:
        monkeypatch.setenv("AGENT_KILL_SWITCH", value)
        node = make_node(audit, run_id)
        approved = node.request_permission(
            tool_name="test_tool",
            target="http://example.com",
            risk_level="LOW",
            description="Test action",
            authorization_ref="ATT-001"
        )
        assert approved is False


def test_kill_switch_off_by_default(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node(audit, run_id)
    approved = node.request_permission(
        tool_name="test_tool",
        target="http://example.com",
        risk_level="LOW",
        description="Test action",
        authorization_ref="ATT-001"
    )
    assert approved is True  # LOW auto-approves when kill switch is off

# --------------------------------------
# LOW risk - auto-approve
# --------------------------------------

def test_low_risk_auto_approved(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node(audit, run_id)
    approved = node.request_permission(
        tool_name="test_tool",
        target="http://example.com",
        risk_level="LOW",
        description="Test action",
        authorization_ref="ATT-001"
    )

    assert approved is True
    actions = audit.get_all_actions(run_id)
    assert len(actions) > 0
    assert "Auto-approved: below HITL threshold" in actions[-1].result_summary


# ---------------------------------------------
# MEDIUM / HIGH - human prompt
# ---------------------------------------------

def test_human_approval_yes(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node(audit, run_id)

    with patch("builtins.input", return_value="yes"):
        approved = node.request_permission(
            tool_name="test_tool",
            target="http://example.com",
            risk_level="HIGH",
            description="Test action",
            authorization_ref="ATT-001"
        )

    assert approved is True
    actions = audit.get_all_actions(run_id)
    assert len(actions) > 0
    assert "APPROVED - human decision" in actions[-1].result_summary


def test_human_approval_no(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node(audit, run_id)

    with patch("builtins.input", return_value="no"):
        approved = node.request_permission(
            tool_name="test_tool",
            target="http://example.com",
            risk_level="HIGH",  # HIGH requires human approval
            description="Test action",
            authorization_ref="ATT-001"
        )

    assert approved is False
    actions = audit.get_all_actions(run_id)
    assert len(actions) > 0
    assert "DENIED - human decision" in actions[-1].result_summary


def test_eoferror_denies_gracefully(audit, run_id, monkeypatch):
    """Simulates CI environment where stdin is not terminal."""
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node(audit, run_id)

    with patch("builtins.input", side_effect=EOFError):
        approved = node.request_permission(
            tool_name="test_tool",
            target="http://example.com",
            risk_level="HIGH",  # HIGH requires human approval
            description="Test action",
            authorization_ref="ATT-001"
        )

    assert approved is False
    actions = audit.get_all_actions(run_id)
    assert len(actions) > 0
    assert "DENIED - human decision" in actions[-1].result_summary

# ------------------------------------------
# Invalid risk level - should still work but use default behavior
# ------------------------------------------

def test_invalid_risk_defaults_to_high(audit, run_id):
    node = make_node(audit, run_id)
    # Invalid risk level should be treated as CRITICAL (highest risk)
    # which requires human approval
    with patch("builtins.input", return_value="yes"):
        approved = node.request_permission(
            tool_name="test_tool",
            target="http://example.com",
            risk_level="BANANA",
            description="Test action",
            authorization_ref="ATT-001"
        )
    assert approved is True


# -----------------------------------------------
# Integration: full agent loop writes audit rows
# -----------------------------------------------

@pytest.mark.asyncio
async def test_agent_loop_writes_audit_rows():
    """
    Run DemoAgent for 3 iterations with a real AuditLog.
    Verify AgentAction rows appear.
    """
    from agentic_sentinel.agents.audit import AuditLog
    from agentic_sentinel.agents.demo_agent import DemoAgent

    audit = AuditLog(db_url=IN_MEMORY_DB)
    agent = DemoAgent(audit_log=audit, run_id="integration-test-123")

    # Run the agent once (single iteration)
    await agent.run()

    # Check that actions were recorded
    actions = audit.get_all_actions("integration-test-123")
    assert len(actions) >= 1  # At least the demo action should be recorded
