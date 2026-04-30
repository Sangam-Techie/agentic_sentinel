
from dataclasses import dataclass
from typing import Any


@dataclass
class Perception:
    target_url: str
    api_map: dict
    raw_findings: list
    metadata: dict

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
    proposed_finding: dict | None
    raw_request: str = ""
    raw_response: str = ""
