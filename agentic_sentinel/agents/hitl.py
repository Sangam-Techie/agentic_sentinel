"""
HITL (Human-In-The-Loop) goverance gate.

PermissionNode must be inserted before any MEDIUM/HIGH/CRITICAL agentaction.
LOW actions are auto-approved and logged.

Impoet with:
    from agentic_sentinel.agents.hitl import PermissionNode
"""

import logging
import os
import secrets

from rich.console import Console
from rich.panel import Panel

from agentic_sentinel.agents.audit import AuditLog

logger = logging.getLogger(__name__)
console = Console()

VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class PermissionNode:
    """
    HITL gate. Behaviour by risk level:

        LOW       -> auto-approved, log entry only, no human interaction
        MEDIUM    -> requires human to type a 6-char token
        HIGH      -> requires human to type a 6-char token (same flow, higher stakes)
        CRITICAL  -> requires human to type a 6-char token + displays a extra warning

    Kill swith (AGENT_KILL_SWITCH=true env var):
        Blocks All actions regardless of risk level.
    """

    def __init__(
        self,
        action_description: str,
        risk: str,
        audit_log: AuditLog,
        run_id: str,
        tool_name: str,
        parameters: dict|None = None
    ):
        if risk not in VALID_RISK_LEVELS:
            raise ValueError(
                f"Invalid risk level '{risk}. Must be one of {VALID_RISK_LEVELS}'"
            )

        self.action = action_description
        self.risk = risk
        self.audit_log = audit_log
        self.run_id = run_id
        self.tool_name = tool_name
        self.parameters = parameters or {}

    # --------------------------------------
    # Internal helpers
    # --------------------------------------

    def _is_kill_switch_active(self) -> bool:
        """
        Check the AGENT_KILL_SWITCH environment variable.
        Returns True only if the result for env equals the string "true"
        """
        return os.getenv("AGENT_KILL_SWITCH", "false").lower() == "true"

    def _generate_token(self) -> str:
        """
        Generate a random 6-character uppercase hex token.
        """
        return secrets.token_hex(3) # this produces 3 random bytes -> 6 hex chars

    def _log(self, approved: bool, reason: str) -> None:
        """Write an AgentAction row to the audit trail."""
        self.audit_log.log_action(
            run_id=self.run_id,
            tool_name=self.tool_name,
            parameters=self.parameters,
            risk_level=self.risk,
            approved=approved,
            approval_reason=reason
        )

    # -------------------------------------------------
    # Public interface
    # --------------------------------------------------

    def request_approval(self) -> bool:
        """
        Main entry point. Returns True if the action may proceed, False if
        blocked.
        """
        # Step 1 - Kill switch
        if self._is_kill_switch_active():
            console.print("\n[bold red]🛑 KILL SWITCH ACTIVE - \
            all agent actions blocked. [/bold red]")
            self._log(approved=False, reason="Kill_switch")
            return False

        # Step 2 - LOW auto-approve
        if self.risk == "LOW":
            logger.debug("Auto-approving LOW risk action: %s", self.action)
            self._log(approved=True, reason="Risk level is 'LOW'")
            return True

        # Step 3 - CRITICAL extra warning
        if self.risk == "CRITICAL":
            console.print(Panel(
                "[bold red]⚠ CRITICAL RISK ACTION[/bold red]\n"
                "This action may be [bold]destructive and irreversible[/bold].\n"
                "Ensure you have explicit written authorisation before proceeding.",
                border_style="red",
                title="CRITICAL RISK",
            ))

        # Step 4: Token prompt
        token = self._generate_token()

        console.print("\n[bold yellow]⚠ HITL APPROVAL REQUIRED[/bold yellow]")
        console.print(f"Proposed action : [cyan]{self.action}[/cyan]")

        risk_colour = {"MEDIUM": "yellow", "HIGH": "red", \
        "CRITICAL": "bold red"}.get(self.risk, "red")
        console.print(f"Risk level    : [{risk_colour}]{self.risk}[/{risk_colour}]")
        console.print(f"Type this token to approve: [bold green]{token}[/bold green]")

        try:
            user_input = input("Token > ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            # Non-interactive environment (CI) or operator pressed Ctrl+C
            console.print("\n[red]Input cancelled - action denied.[/red]")
            self._log(approved=False, reason="human denied")
            return False

        if user_input == token:
            console.print("[green]✅ Token accepted - action approved.[/green]")
            self._log(approved=True, reason="Token accepted")
            return True
        else:
            console.print("[red]x Incorrect token - action denied.[/red]")
            self._log(approved=False, reason="Wrong Token")
            return False
