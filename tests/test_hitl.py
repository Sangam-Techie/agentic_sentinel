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
    return AuditLog(database_url=IN_MEMORY_DB)

@pytest.fixture
def run_id(audit: AuditLog) -> str:
    run = audit.start_run("test", "localhost", "att.md")
    return run.id

def make_node(risk: str, audit: AuditLog, run_id: str) -> PermissionNode:
    return PermissionNode(
        action_description="test_action",
        risk=risk,
        audit_log=audit,
        run_id=run_id,
        tool_name="test_tool",
        parameters={"key":"val"}
    )


# --------------------------------------
# Kill switch tests
# --------------------------------------

def test_kill_switch_blocks_low(audit, run_id, monkeypatch):
    monkeypatch.setenv("AGENT_KILL_SWITCH", "true")
    node = make_node("LOW", audit, run_id)
    approved = node.request_approval()

    assert approved is False
    actions = audit.get_actions_for_run(run_id)
    assert actions[0].approval_reason == "Kill_switch"

def test_kill_switch_blocks_high(audit, run_id, monkeypatch):
    monkeypatch.setenv("AGENT_KILL_SWITCH", "true")
    node = make_node("HIGH", audit, run_id)
    approved = node.request_approval()

    assert approved is False
    assert audit.get_actions_for_run(run_id)[0].approval_reason == "Kill_switch"

def test_kill_switch_case_insensitive(audit, run_id, monkeypatch):
    # "TRUE", "True", "true" must all activate the kill switch
    for value in ["TRUE", "True", "true"]:
        monkeypatch.setenv("AGENT_KILL_SWITCH", value)
        node = make_node("LOW", audit, run_id)
        assert node.request_approval() is False

def test_kill_switch_off_by_default(audit, run_id, monkeypatch):
    monkeypatch.delenv("Agent_KILL_SWITCH", raising=False)
    node = make_node("LOW", audit, run_id)
    approved = node.request_approval()
    assert approved is True # LOW auto-approves when kill switch is off

# --------------------------------------
# LOW risk - auto-approve
# --------------------------------------

def test_low_risk_auto_approved(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node("LOW", audit, run_id)
    approved = node.request_approval()

    assert approved is True
    action = audit.get_actions_for_run(run_id)[0]
    assert action.approved is True
    assert action.approval_reason == "Risk level is 'LOW'"


# ---------------------------------------------
# MEDUIM / HIGH - token prompt
# ---------------------------------------------

def test_correct_token_approves(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node("HIGH", audit, run_id)
    # Intercept _generate_token so we know what to "type"
    fixed_token = "ABC123" # noqa: S105 - test token, not a real password
    with patch.object(node, "_generate_token", return_value=fixed_token):
        with patch("builtins.input", return_value=fixed_token):
            approved = node.request_approval()

    assert approved is True
    action = audit.get_actions_for_run(run_id)[0]
    assert action.approved is True
    assert action.approval_reason == "Token accepted"

def test_wrong_token_denies(audit, run_id, monkeypatch):
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node("HIGH", audit, run_id)

    with patch.object(node, "_generate_token", return_value="ABC123"):
        with patch("builtins.input", return_value="WRONG1"):
            approved = node.request_approval()

    assert approved is False
    action = audit.get_actions_for_run(run_id)[0]
    assert action.approved is False
    assert action.approval_reason == "Wrong Token"

def test_eoferror_denies_gracefully(audit, run_id, monkeypatch):
    """Simulates CI environment where stdin is not terminal."""
    monkeypatch.delenv("AGENT_KILL_SWITCH", raising=False)
    node = make_node("MEDIUM", audit, run_id)

    with patch.object(node, "_generate_token", return_value="XYZ789"):
        with patch("builtins.input", side_effect=EOFError):
            approved = node.request_approval()

    assert approved is False
    assert audit.get_actions_for_run(run_id)[0].approval_reason == "human denied"

# ------------------------------------------
# Invalid risk leevl
# ------------------------------------------

def test_invalid_risk_raises(audit, run_id):
    with pytest.raises(ValueError, match="Invalid risk level"):
        PermissionNode(
            action_description="bad",
            risk="BANANA",
            audit_log=audit,
            run_id=run_id,
            tool_name="tool",
        )

# -----------------------------------------------
# Integration: full agent loop writes audit rows
# -----------------------------------------------

@pytest.mark.asyncio
async def test_agent_loop_writes_audit_rows():
    """
    Run DemoAgent for 3 iterations with a real AuditLog.
    Verity AgentRun is created and AgentAction row appear.
    """
    from agentic_sentinel.agents.audit import AuditLog
    from agentic_sentinel.agents.base import DemoAgent

    audit = AuditLog(database_url=IN_MEMORY_DB)
    agent = DemoAgent(
        name="audit-test",
        max_iterations=3,
        loop_interval=0,
        audit_log=audit,
        operator="pytest",
        target_scope="localhost",
        authorization_ref="att.md",
    )
    await agent.run_loop()

    assert agent.run_id is not None
    actions = audit.get_actions_for_run(agent.run_id)
    # 3 iterations x 1 observe() call each = 3 action rows minimum
    assert len(actions) >= 3

    # The run should be marked completed
    from sqlmodel import Session
    with Session(audit.engine) as session:
        from agentic_sentinel.agents.audit import AgentRun
        run = session.get(AgentRun, agent.run_id)
    assert run.status == "completed"
    assert run.finished_at is not None
