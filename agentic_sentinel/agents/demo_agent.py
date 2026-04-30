
import asyncio

from agentic_sentinel.agents.audit import AgentAction, AuditLog
from agentic_sentinel.agents.base import AgentBase
from agentic_sentinel.agents.types import ActionResult, AgentDecision, Perception


class DemoAgent(AgentBase):
    """
    Smoke test agent. Proves the four-method loop, HITL gate,
    and AuditLog all wire together correctly.
    No HTTP requests. No real target interaction.
    """

    async def perceive(self) -> Perception:
        return Perception(
            target_url="http://localhost:9090",
            api_map={"endpoints": ["/api/v1/demo"]},
            raw_findings=[],
            metadata={"note": "demo - no real requests"},
        )

    async def reason(self, perception: Perception) -> AgentDecision:
        return AgentDecision(
            action="demo_action",
            target_endpoint=perception.api_map["endpoints"][0],
            tool_to_use="DemoTool",
            risk_level="LOW",
            reasoning="Demo agent always takes the demo action",
            confidence=1.0,
        )

    async def act(self, decision: AgentDecision) -> ActionResult:
        self.audit_log.record(AgentAction(
            run_id=self.run_id,
            tool="DemoAgent.act",
            target=decision.target_endpoint,
            risk_level=decision.risk_level,
            result_summary="Demo action completed - no real request sent",
            authorization_ref="ATT-000-DEMO",
        ))
        return ActionResult(
            success=True,
            tool_used="DemoTool",
            target=decision.target_endpoint,
            response_status=None,
            response_body=None,
            proposed_finding=None,
        )

    async def observe(self, result: ActionResult) -> None:
        pass

if __name__ == "__main__":
    log = AuditLog()
    agent = DemoAgent(audit_log=log, run_id="demo-001")
    asyncio.run(agent.run())

    entries = log.tail_jsonl(n=5)
    print(f"\nLast {len(entries)} audit entries:")
    for e in entries:
        print(f" [{e['risk_level']}] {e['tool']} -> {e['result_summary']}")
