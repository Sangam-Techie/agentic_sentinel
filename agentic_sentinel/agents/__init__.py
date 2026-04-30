"""
Public API for the agents package.
Most code should import from here, not from submodules directly.

    from agentic_sentinel.agents import AgentBase, DemoAgent
    from agentic_sentinel.agents import Perception, AgentDecision, ActionResult
    from agentic_sentinel.agents import AgentBase, AuditLog, PermissionNode
"""

from agentic_sentinel.agents.types import ActionResult, AgentDecision, Perception

__all__ = [
    "AgentBase",
    "DemoAgent",
    "Perception",
    "AgentDecision",
    "ActionResult",
    "AgentAction",
    "AuditLog",
    "PermissionNode"
]


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency issues when running modules directly."""
    if name == "AgentAction":
        from agentic_sentinel.agents.audit import AgentAction
        return AgentAction
    elif name == "AuditLog":
        from agentic_sentinel.agents.audit import AuditLog
        return AuditLog
    elif name == "PermissionNode":
        from agentic_sentinel.agents.hitl import PermissionNode
        return PermissionNode
    elif name == "AgentBase":
        from agentic_sentinel.agents.base import AgentBase
        return AgentBase
    elif name == "DemoAgent":
        from agentic_sentinel.agents.base import DemoAgent
        return DemoAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
