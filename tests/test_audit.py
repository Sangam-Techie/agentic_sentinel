"""
Tests for AuditLog - database operations.
Uses an in-memory SQLite DB so no files are created during CI.
"""

import json

import pytest

from agentic_sentinel.agents.audit import AgentRun, AuditLog

IN_MEMORY_DB = "sqlite://"  # In-memorry SQLITE

@pytest.fixture
def audit() -> AuditLog:
    """Fresh in-memory AuditLog for each test."""
    return AuditLog(database_url=IN_MEMORY_DB)

def test_start_run_creates_row(audit: AuditLog):
    run = audit.start_run(
        operator="test_user",
        target_scope="localhost",
        authorization_ref="aii.md",
    )
    assert isinstance(run, AgentRun)
    assert run.id is not None
    assert run.status == "running"
    assert run.operator == "test_user"

def test_finish_run_updates_status(audit: AuditLog):
    run = audit.start_run("u", "localhost", "att.md")
    audit.finish_run(run.id, status="completed")

    # Re-read from DB to verify persistence
    from sqlmodel import Session
    with Session(audit.engine) as session:
        updated = session.get(AgentRun, run.id)
    assert updated.status == "completed"
    assert updated.finished_at is not None


def test_finish_run_unknown_id_does_not_raise(audit: AuditLog):
    # Should log a warning and return gracefully - not raise
    audit.finish_run("nonexistent-id", status="completed")


def test_log_action_creates_row(audit: AuditLog):
    run = audit.start_run("u", "localhost", "att.md") # noqa: F841
    action = audit.log_action(
        run_id="nonexistent",   # deliberately wrong - FK not enforced in SQlite by default
        tool_name="port_scan",
        parameters={"host": "127.0.0.1", "port": 80},
        risk_level="LOW",
        approved=True,
        approval_reason="auto_low",
        result_summary="port open"
    )
    assert action.id is not None
    assert action.tool_name == "port_scan"
    assert action.approved is True
    assert action.approval_reason == "auto_low"
    # parameters stored as Json string
    assert json.loads(action.parameters) == {"host": "127.0.0.1", "port": 80}


def test_get_actions_for_run(audit: AuditLog):
    run = audit.start_run("u", "localhost", "att.md")
    audit.log_action(run.id, "scan_a", {}, "LOW", True, "auto_low")
    audit.log_action(run.id, "scan_b", {}, "HIGH", False, "human_denied")

    actions = audit.get_actions_for_run(run.id)
    assert len(actions) == 2
    tool_names = {a.tool_name for a in actions}
    assert tool_names == {"scan_a", "scan_b"}


def test_get_actions_empty_for_unknown_run(audit: AuditLog):
    actions = audit.get_actions_for_run("no-such-run")
    assert  actions == []
