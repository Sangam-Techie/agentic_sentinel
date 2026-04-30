
from agentic_sentinel.agents.audit import AuditLog
from agentic_sentinel.agents.demo_agent import DemoAgent
from agentic_sentinel.agents.types import Perception

IN_MEMORY_DB = "sqlite://"


# ======================================================
# TEST 1: DemoAgent perceive() returns correct Perception
# =======================================================


async def test_perceive_returns_perception():
    audit = AuditLog(db_url=IN_MEMORY_DB)
    agent = DemoAgent(audit_log=audit, run_id="test-1")
    perception = await agent.perceive()

    # check if perception is a Perception instance
    assert isinstance(perception, Perception)

    # check if the perception has the expected structure
    assert perception.target_url == "http://localhost:9090"
    assert "endpoints" in perception.api_map
    assert perception.metadata["note"] == "demo - no real requests"


# ==========================================================
# TEST 2: DemoAgent reason() returns demo action on healthy state
# ==========================================================


async def test_reason_returns_demo_action():
    audit = AuditLog(db_url=IN_MEMORY_DB)
    agent = DemoAgent(audit_log=audit, run_id="test-2")
    perception = await agent.perceive()
    decision = await agent.reason(perception)

    # check if decision.action == "demo_action"
    assert decision.action == "demo_action"

    # check if decision.risk_level == "LOW"
    assert decision.risk_level == "LOW"

    # check if decision.tool_to_use == "DemoTool"
    assert decision.tool_to_use == "DemoTool"

# =========================================================
# TEST 3: DemoAgent act() returns ActionResult
# =========================================================


async def test_act_returns_action_result():
    from agentic_sentinel.agents.types import ActionResult

    audit = AuditLog(db_url=IN_MEMORY_DB)
    agent = DemoAgent(audit_log=audit, run_id="test-3")
    perception = await agent.perceive()
    decision = await agent.reason(perception)
    result = await agent.act(decision)

    # check if result is an ActionResult instance
    assert isinstance(result, ActionResult)

    # check if action was successful
    assert result.success is True

    # check if tool_used is "DemoTool"
    assert result.tool_used == "DemoTool"


# ==================================================
# TEST 4: Agent run() method executes the full loop
# ==================================================


async def test_run_executes_full_loop():
    """
    The run() method should execute perceive -> reason -> act -> observe
    """
    audit = AuditLog(db_url=IN_MEMORY_DB)
    agent = DemoAgent(audit_log=audit, run_id="test-4")

    # Run the agent
    await agent.run()

    # Check that actions were recorded in audit log
    actions = audit.get_all_actions("test-4")
    assert len(actions) >= 1  # At least the demo action should be recorded

    # Check that the action has the expected properties
    action = actions[0]
    assert "DemoAgent.act" in action.tool
    assert action.risk_level == "LOW"
