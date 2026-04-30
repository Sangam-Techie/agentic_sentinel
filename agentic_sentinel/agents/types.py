
from dataclasses import dataclass
from typing import Any


@dataclass
class Perception:
    target_url: str
    api_map: dict[str, Any]
    raw_findings: list[Any]
    metadata: dict[str, Any]

@dataclass
class AgentDecision:
    action: str
    target_endpoint: str
    tool_to_use: str
    risk_level: str
    reasoning: str
    confidence: float

@dataclass
class ActionResult:
    success: bool
    tool_used: str
    target: str
    response_status: int | None
    response_body: Any
    proposed_finding: dict[str, Any] | None
    raw_request: str = ""
    raw_response: str = ""
