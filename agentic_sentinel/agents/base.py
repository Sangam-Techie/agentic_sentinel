"""
Abstract base class for all Agentic Sentinel agents.

Import with:
    from agentic_sentinel.agents.base import AgentBase, DemoAgent
"""
import asyncio
import logging
from abc import ABC, abstractmethod

from rich.console import Console

from agentic_sentinel.agents.audit import AuditLog
from agentic_sentinel.agents.hitl import PermissionNode
from agentic_sentinel.agents.types import ActionResult, AgentDecision, Perception

__all__ = ["AgentBase", "DemoAgent"]
console = Console()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# =====================================================
# SECTION 1: Abstract base class
# =====================================================

class AgentBase(ABC):
    """
    Abstract base class for all Agentic Sentinel agents.

    Subclasses MUST implement: perceive(), reason(), act()
    Subclasses MAY override: observe(), on_start(), on_stop()

    The run_loop() method orchestrates the four phases.
    """

    def __init__(
        self,
        name: str,
        loop_interval: float = 5.0,    # seconds between iterations
        max_iterations: int|None = None, # None = run forever
        audit_log: AuditLog|None = None,
        operator: str = "cli",
        target_scope: str = "localhost",
        authorization_ref: str = "att.md"
    ):
        self.name = name
        self.loop_interval = loop_interval
        self.max_iterations = max_iterations
        self.iteration = 0
        self.stop_event = asyncio.Event() # To stop loop cleanly
        self.audit_log = audit_log
        self.run_id: str|None = None
        self._operator = operator
        self._target_scope = target_scope
        self._authorization_ref = authorization_ref

        # --------------------------------------------------
        # Abstract methods - subclasses must implement these
        #----------------------------------------------------

    @abstractmethod
    async def perceive(self) -> Perception:
        """
        Gather observations from the environment.
        Examples: read a network interface, poll an API, parse a log file.
        Must return a Perception object.
        """
        ...

    @abstractmethod
    async def reason(self, perception: Perception) -> AgentDecision:
        """
        Decide what to do based on what was perceived.
        Examples: LLM call, rule match, anomaly score threshold
        Must return an AgentDecision object
        """
        ...

    @abstractmethod
    async def act(self, decision: AgentDecision) -> ActionResult:
        """
        Execute the decision (or gate it behind HITL if risk is MEDIUM+).
        Must return an ActionResult object.
        IMPORTANT: HIGH/CRITICAL actions must NEVER execute without HITL approval.
        PermissionNode will be wired here in later days.
        """
        ...

    # ------------------------------------------------------
    # Concrete methods - implemented here, can be overridden
    # ------------------------------------------------------

    async def observe(self, result: ActionResult) -> None:
        """
        Record what happend after act().
        Default implementation: log to console.
        In Day 3, this will get extended to write to the SQLite audit trail.
        """
        if result.success:
            console.print(
                f"[green]✅{self.name} iter={self.iteration} "
                f"action={result.action_name} SUCCESS [/green]"
            )
        else:
            console.print(
                f"[red]x action={result.action_name} FAILED, Error:{result.error} [/red]"
            )

        # Send to the Python logger
        logger.info(
            "action=%s success=%s error=%s",
            result.action_name,
            result.success,
            result.error or "none"
        )

        # Write to audit trail if configured
        if self.audit_log and self.run_id:
            self.audit_log.log_action(
                run_id=self.run_id,
                tool_name=result.action_name,
                parameters=result.output,
                risk_level="LOW",
                approved=True,
                approval_reason="auto_low",
                result_summary="success" if result.success else None,
                error=result.error or None,
            )


    async def on_start(self) -> None:
        """Called once before the loop begins. Override for setup work."""
        console.print(f"\n[bold cyan]▶ Agent '{self.name} starting.[/bold cyan]")
        # open an AgentRun row
        if self.audit_log:
            run = self.audit_log.start_run(
                operator=self._operator,
                target_scope=self._target_scope,
                authorization_ref=self._authorization_ref
            )
            self.run_id = run.id
            console.print(f"[dim]Audit run ID: {self.run_id}[/dim]")

    async def on_stop(self) -> None:
        """Called once after the loop ends. Override for teardown work."""
        console.print(
            f"\n[bold yellow]■ Agent '{self.name}' stopped "
            f"after {self.iteration} iteration(s).[/bold yellow]"
        )
        # close the AgentRun row
        if self.audit_log and self.run_id:
            self.audit_log.finish_run(self.run_id, status="completed")


    # -------------------------------------------------------------------
    # The main loop - do not override unless known the reason to override
    # --------------------------------------------------------------------

    async def run_loop(self) -> None:
        """
        Orchestrates the perceive -> reason -> act -> observe cycle.
        """
        await self.on_start()

        while not self.stop_event.is_set():
            try:
                self.iteration += 1

                perception = await self.perceive()
                decision = await self.reason(perception)
                result = await self.act(decision)
                await self.observe(result)

                if self.max_iterations is not None and self.iteration >= self.max_iterations:
                    self.stop_event.set()

                await asyncio.sleep(self.loop_interval)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Iteration %d failed: %s", self.iteration, e)
                # mark run as abortd if an unhandled error escapes
                if self.audit_log and self.run_id:
                    self.audit_log.finish_run(self.run_id, status="aborted")
                raise

        await self.on_stop()

    def stop(self) -> None:
        """Thread-safe method to stop the loop from outside."""
        self.stop_event.set()

# ===================================================
# SECtION 2: Concrete stub for demo/testing
# ===================================================

class DemoAgent(AgentBase):
    """
    A minimal concrete agent for demonstration.
    Does not connect to any real network or device.
    """

    async def perceive(self) -> Perception:
        return Perception(
            source="demo",
            data={"ping": "ok"}
        )

    async def reason(self, perception: Perception) -> AgentDecision:
        if perception.data.get("ping") == "ok":
            return AgentDecision(
                action_name="no_op",
                risk_level="LOW",
                rationale="This is just a simulation check"
            )
        return AgentDecision(
            action_name="alert",
            risk_level="HIGH",
            rationale="Unexpected ping state detected.",
        )

    async def act(self, decision: AgentDecision) -> ActionResult:
        # IF Higher then, printing warning(will add HTITL later)
        if decision.risk_level == "LOW" and self.audit_log and self.run_id:
            gate = PermissionNode(
                action_description=f"{decision.action_name}: {decision.rationale}",
                risk=decision.risk_level,
                audit_log=self.audit_log,
                run_id=self.run_id,
                tool_name=decision.action_name,
                parameters=decision.parameters,
            )
            if not gate.request_approval():
                return ActionResult(
                    success=False,
                    action_name=decision.action_name,
                    error="Blocked by HITL gate",
                )
        return ActionResult(
            success=True,
            action_name=decision.action_name,
            output={"rationale": decision.rationale}
        )
        # # Non-Low path (placeholder untill day 3)
        # console.print(
        #     f"[yellow]⚠ HITL required for {decision.risk_level} action "
        #     f"'{decision.action_name}' - blocked until Day 3 or 4 wiring.[/yellow]"
        # )
        # return ActionResult(
        #     success=False,
        #     action_name=decision.action_name,
        #     error="HITL gate not yet wired",
        # )


# ===============================================
# SECTION 3: Demo entrypoint
# ================================================

if __name__ == "__main__":
    audit = AuditLog(database_url="sqlite:///demo_audit.sqlite")
    # Running the DemoAgent for exactly 3 iterations with a 1-second interval.
    agent = DemoAgent(
        name="sentinel-demo",
        max_iterations=3,
        loop_interval=1.0,
        audit_log=audit,
        operator="student",
        target_scope="localhost",
        authorization_ref="authorization_to_test.md",
    )
    asyncio.run(agent.run_loop())
