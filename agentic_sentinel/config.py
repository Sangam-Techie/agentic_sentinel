"""
Central configuration for Agentic Sentinel.
All environment variables and shared constants live here.
Import with: from agentic_sentinel.config import settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    agent_kill_switch: bool = False
    database_url: str = "sqlite:///agent_audit.sqlite"
    llm_backend: str = "local"
    ollama_base_url: str = "http://localhost:11434"

    class Config:
        env_file = ".env"

settings = Settings()
