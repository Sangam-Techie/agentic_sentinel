"""
Audit trail schema and helper for Agentic Sentinel.

Tables:
    - AgentRun : one row per top-level agent invocation
    - AgentAction : one row per atomic action within a run

Import with:
    from agentic_sentinel.agents.audit import AgentRun, AgentAction, AuditLog
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, create_engine, select

from agentic_sentinel.config import settings

logger = logging.getLogger(__name__)


# =================================================
# SECTION 1: Database table schemas
# =================================================

class AgentRun(SQLModel, table=True):
    """
    One top-level invocation of the agent pipeline.
    Created when run_loop() starts; updated when it ends.
    """

    # Primary key: UUID string, auto-generated
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # When the run started - auto-set to UTC now
    started_at: datetime = Field(default_factory=lambda :datetime.now(UTC))

    # When the run finished - None until the agent stops
    finished_at: datetime|None = Field(default=None)

    # Current status of the run
    # Values: "running" | "completed" | "aborted" | "Killed"
    status: str = Field(default="running")

    # Who launched this run (username, API token, or "cli")
    operator: str

    # The authorised scope string (e.g. "192.168.1.0/24 - lab containers")
    target_scope: str

    # Filename or SHA-256 hash of the signed ATT form
    authorization_ref : str


class AgentAction(SQLModel, table=True):
    """
    One atomic action taken (or blocked) withing an AgentRun.
    Created by AuditLog.log_action() inside PermissionNode
    """

    # Primary key: UUID string, auto-generated
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Foreign key back to the parent AgentRun
    run_id: str = Field(foreign_key="agentrun.id")

    # When this action was recorded
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Name of the tool or action (e.g. "port_scan", "credential_attempt")
    tool_name: str

    # Json string of the action parameters (use .model_dump_json() before storing)
    parameters: str = Field(default={})

    # LOW | MEDIUM | HIGH | CRITICAL
    risk_level : str

    # Was this action approved?
    approved: bool

    # Why it was approved or denied
    # Values: "auto_low" | "human_approved" | "human_denied" | "kill_switch"
    approval_reason: str

    # Brief human-readable summary of what happened
    result_summary: str|None = Field(default=None)

    # Error message if the action failed
    error: str|None = Field(default=None)


# ==============================================
# SECTION 2: Database engine factory
# =============================================

def create_db_engine(database_url: str|None = None):
    """
    Create and return a SQLModel engine, creating all tables if needed.
    """
    url = database_url or settings.database_url
    engine = create_engine(
        url,
        echo=False,
        connect_args={"check_same_thread": False}, # Required for SQLite + asyncio
    )
    SQLModel.metadata.create_all(engine)
    return engine

# =============================================
# SECTION 3: AuditLog helper
# =============================================

class AuditLog:
    """
    High-level helper that wraps raw SQLModel operations.
    Injected into PermissionNode and AgentBase so they never
    touch the database engine directly.

    Usage:
        audit = AuditLog()
        run = audit.start_run(operator="cli", target_scope="localhhost",
            authrization_ref="att_v1.md")
        audit.log_action(run_id=run.id, tool_name="port_scan", ...)
        audit.finish_run(run_id=run.id, status="completed")
    """

    def __init__(self, database_url: str|None = None):
        self.engine = create_db_engine(database_url)

    def start_run(
        self,
        operator: str,
        target_scope: str,
        authorization_ref: str,
    ) -> AgentRun:
        """
        Insert a new AgentRun row with status="running".
        Return the created AgentRun object (with its generated id).
        """
        run = AgentRun(
            operator=operator,
            target_scope=target_scope,
            authorization_ref=authorization_ref
        )
        with Session(self.engine) as session:
            session.add(run)
            session.commit()
            session.refresh(run)
        return run

    def finish_run(self, run_id: str, status: str) -> None:
        """
        Update an existing AgentRun: set finished_at=now and status=status.
        """
        with Session(self.engine) as session:
            run = session.get(AgentRun, run_id)
            if not run:
                logger.warning("finish_run: run_id %s not found", run_id)
                return
            run.finished_at = datetime.now(UTC)
            run.status = status
            session.add(run)
            session.commit()

    def log_action(
        self,
        run_id: str,
        tool_name: str,
        parameters: dict,
        risk_level: str,
        approved: bool,
        approval_reason: str,
        result_summary: str|None = None,
        error: str|None = None
    ) -> AgentAction:
        """
        Insert a new AgentAction row.
        parameters dict is serialised to JSON before storage.
        Returns the created AgentAction.
        """
        action = AgentAction(
            run_id=run_id,
            tool_name=tool_name,
            parameters=json.dumps(parameters),
            risk_level=risk_level,
            approved=approved,
            approval_reason=approval_reason,
            result_summary=result_summary,
            error=error
        )
        with Session(self.engine) as session:
            session.add(action)
            session.commit()
            session.refresh(action)
        return action

    def get_actions_for_run(self, run_id: str) -> list[AgentAction]:
        """
        Return all AgentAction rows for a given run_id, ordered by timestamp.
        """
        with Session(self.engine) as session:
            statement = select(AgentAction).where(AgentAction.run_id == run_id)
            return list(session.exec(statement).all())
