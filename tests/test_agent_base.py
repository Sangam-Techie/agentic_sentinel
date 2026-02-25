
from agentic_sentinel.agents import DemoAgent, Perception

# ======================================================
# TEST 1: DemoAgent perceive() returns correct Perception
# =======================================================


async def test_perceive_returns_perception():
    agent = DemoAgent(name="test", max_iterations=1, loop_interval=0)
    perception = await agent.perceive()

    # check if perception is a Perception instance
    assert isinstance(perception, Perception)

    # check of the perception ping value is ok
    assert perception.data["ping"] == "ok"

    # check if perception source equals to "demo"
    assert perception.source == "demo"


# ==========================================================
# TEST 2: DemoAgent reason() returns no_op on healthy ping
# ==========================================================


async def test_reason_no_op_on_healthy():
    agent = DemoAgent(name="test", max_iterations=1, loop_interval=0)
    perception = Perception(source="demo", data={"ping": "ok"})
    decision = await agent.reason(perception)

    # check if descision.action_name == "no_op"
    assert decision.action_name == "no_op"

    # check if decision.risk_level == "LOW"
    assert decision.risk_level == "LOW"

# =========================================================
# TEST 3: DemoAgent reason() returns alert on bad ping
# =========================================================


async def test_reason_alert_on_bad_ping():
    agent = DemoAgent(name="test", max_iterations=1, loop_interval=0)
    perception = Perception(source="demo", data={"ping": "timeout"})
    decision = await agent.reason(perception)

    # check if action_name is "alert"
    assert decision.action_name == "alert"

    # check if risk_level is not "LOW"
    assert decision.risk_level != "LOW"

# ==================================================
# TEST 4: run_loop() executes exactly N iterations
# ==================================================


async def test_loop_runs_exact_iterations():
    """
    The loop must stop after max_iterations and not run one extra.
    """
    n = 3
    agent = DemoAgent(name="test", max_iterations=n, loop_interval=0)

    # check the run.loop() with asyncio
    await agent.run_loop()

    # check the iteration value
    assert agent.iteration == n


# ============================================
# TEST 5: stop_event halts the loop early
# ============================================


async def test_stop_event_halts_loop():
    """
    Calling agent.stop() during the loop must halt it before max_iterations.
    Strategy: set max_iterations=100 (would take forever),
            but schedule a stop after 2 iterations using a side-effect.
    """
    agent = DemoAgent(name="test", max_iterations=100, loop_interval=0)

    # monkeypath observe() to stop the agent after 2 calls
    call_count = {"n": 0}
    original_observe = agent.observe

    async def observe_and_maybe_stop(result):
        await original_observe(result)
        call_count["n"] += 1
        if call_count["n"] >= 2:
            agent.stop()  #stop the event

    agent.observe = observe_and_maybe_stop
    await agent.run_loop()

    # check if agent stopped at or near 2 iterations(not 100)
    assert agent.iteration <= 2
