from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Perception:
    """
    The raw observations from one perceive() call.
    Think: everything the agent's 'senses' returned this iteration.
    """
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown" #e.g. "network_scan", "camera_feed", "log_file"


@dataclass
class AgentDecision:
    """
    The output of reason(): what action should be taken and at what risk level.
    """
    action_name: str  # e.g. "port_scan", "alert", "no_op"
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    rationale: str = ""      # Human-readable explanation of why


@dataclass
class ActionResult:
    """
    The output of act(): what actually happened.
    """
    success: bool
    action_name: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
