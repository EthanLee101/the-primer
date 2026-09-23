from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://primer:primer@localhost:5432/primer"
    llm_provider: Literal["gemini", "fake"] = "fake"
    gemini_api_key: str | None = None
    # explicit allowlist, never "*" — the frontend runs on its own origin/port
    cors_origins: list[str] = ["http://localhost:5173"]
    # per-IP; the endpoint that calls Gemini. Generous for real practice
    # (a kid isn't organically answering faster than this), tight enough to
    # bound worst-case free-tier quota/cost exposure from a runaway client.
    answer_rate_limit: str = "20/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
