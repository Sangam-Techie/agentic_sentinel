"""
Central configuration for Agentic Sentinel.
All environment variables and shared constants live here.
Import with: from agentic_sentinel.config import settings
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Agent behavior
    agent_kill_switch: bool = field(
        default_factory=lambda: os.getenv("AGENT_KILL_SWITCH", "false").lower() == "true"
    )
    default_loop_interval: float = float(os.getenv("LOOP_INTERVAL_SECONDS", "5.0"))
    max_actions_per_minute: int = int(os.getenv("MAX_ACTIONS_PER_MINUTE", "10"))

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///agent_audit.sqlite")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
