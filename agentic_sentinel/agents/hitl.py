"""
HITL (Human-In-The-Loop) goverance gate.

PermissionNode must be inserted before any MEDIUM/HIGH/CRITICAL agentaction.
LOW actions are auto-approved and logged.

Impoet with:
    from agentic_sentinel.agents.hitl import PermissionNode
"""

import os

from rich.console import Console

from agentic_sentinel.agents.audit import AgentAction, AuditLog

console = Console()

class PermissionNode:
    RISK_THRESHOLDS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    AUTO_APPROVE_BELOW = 2

    def __init__(self, audit_log: AuditLog, run_id: str):
        self.audit_log = audit_log
        self.run_id = run_id

    def request_permission(
            self,
            tool_name: str,
            target: str,
            risk_level: str,
            description: str,
            authorization_ref: str
    ) -> bool:
        if os.getenv("AGENT_KILL_SWITCH", "false").lower() == "true":
            console.print(f"[yellow][PermissionNode] 🛑 KILL SWITCH ACTIVE - blocking {tool_name}[/yellow]")
            self._log(tool_name, target, risk_level, authorization_ref,
                      approved=False, reason="KILL SWITCH ACTIVE")
            return False

        risk_score = self.RISK_THRESHOLDS.get(risk_level, 3)

        if risk_score < self.AUTO_APPROVE_BELOW:
            self._log(tool_name, target, risk_level, authorization_ref,
                      approved=True, reason="Auto-approved: below HITL threshold")
            return True
        console.print(f"\n[bold red]{'='*60}[/bold red]")
        console.print(f"""[bold red] ⚠️ HITL GATE - {risk_level} RISK ACTION REQUIRES APPROVAL[/bold red]
                      Tool: {tool_name}
                      Target: {target}
                      Description: {description}
                      Authorization Reference: {authorization_ref}
                      """)
        console.print(f"[bold red]{'='*60}[/bold red]")
        try:
            answer = input(" Approve? (yes/no): ").strip().lower()
            approved = answer == "yes"
        except (EOFError, KeyboardInterrupt):
            # In CI/non-interactive environments, deny by default
            approved = False

        self._log(tool_name, target, risk_level, authorization_ref,
                  approved=approved, reason="human decision")
        return approved

    def _log(self, tool, target, risk_level, auth_ref, approved, reason):
        self.audit_log.record(AgentAction(
            run_id=self.run_id,
            tool=f"PermissionNode:{tool}",
            target=target,
            risk_level=risk_level,
            result_summary=f"{'APPROVED' if approved else 'DENIED'} - {reason}",
            authorization_ref=auth_ref,
            proposed=False,
            confirmed=False,
        ))
