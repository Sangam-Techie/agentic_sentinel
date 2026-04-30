

from abc import ABC, abstractmethod

from agentic_sentinel.agents.audit import AuditLog
from agentic_sentinel.agents.types import ActionResult, AgentDecision, Perception


class AgentBase(ABC):
    def __init__(self, audit_log: AuditLog, run_id: str):
        self.audit_log = audit_log
        self.run_id = run_id

    @abstractmethod
    async def perceive(self) -> Perception:
        """Gather information. No state-modifying requests."""
        ...

    @abstractmethod
    async def reason(self, perception: Perception) -> AgentDecision:
        """Decide what to do. No network calls to target"""
        ...

    @abstractmethod
    async def act(self, decision: AgentDecision) -> ActionResult:
        """Execute approved action. Must check HITL for HIGH/CRITICAL."""
        ...

    @abstractmethod
    async def observe(self, result: ActionResult) -> None:
        """Record result. Run VerificationEngine from Epoch 1 onward."""
        ...

    async def run(self) -> None:
        """
        Template method — do NOT override.
        Overriding bypasses the governance guarantee.
        """
        perception = await self.perceive()
        decision = await self.reason(perception)
        result = await self.act(decision)
        await self.observe(result)
