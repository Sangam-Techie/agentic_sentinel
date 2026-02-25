import asyncio
import logging
from abc import ABC, abstractmethod

from rich.console import Console

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
        max_iterations: int|None = None # None = run forever
    ):
        self.name = name
        self.loop_interval = loop_interval
        self.max_iterations = max_iterations
        self.iteration = 0
        self.stop_event = asyncio.Event() # To stop loop cleanly

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


    async def on_start(self) -> None:
        """Called once before the loop begins. Override for setup work."""
        console.print(f"\n[bold cyan]▶ Agent '{self.name} starting.[/bold cyan]")

    async def on_stop(self) -> None:
        """Called once after the loop ends. Override for teardown work."""
        console.print(
            f"\n[bold yellow]■ Agent '{self.name}' stopped "
            f"after {self.iteration} iteration(s).[/bold yellow]"
        )


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
        if decision.risk_level == "LOW":
            return ActionResult(
                success=True,
                action_name=decision.action_name,
                output={"rationale": decision.rationale}
            )
        # Non-Low path (placeholder untill day 3)
        console.print(
            f"[yellow]⚠ HITL required for {decision.risk_level} action "
            f"'{decision.action_name}' - blocked until Day 3 or 4 wiring.[/yellow]"
        )
        return ActionResult(
            success=False,
            action_name=decision.action_name,
            error="HITL gate not yet wired",
        )


# ===============================================
# SECTION 3: Demo entrypoint
# ================================================

if __name__ == "__main__":
    # Running the DemoAgent for exactly 3 iterations with a 1-second interval.
    agent = DemoAgent(
        name="sentinel-demo",
        max_iterations=3,
        loop_interval=1,
    )
    asyncio.run(agent.run_loop())
