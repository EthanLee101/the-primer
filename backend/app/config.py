import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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
    # per-IP; login/register are brute-force/credential-stuffing targets, so
    # this is deliberately much tighter than answer_rate_limit.
    auth_rate_limit: str = "5/minute"
    # No hardcoded fallback secret — that's a real vulnerability if it ever
    # ships. If JWT_SECRET_KEY isn't set, each process gets a fresh random
    # one at startup, which just invalidates existing sessions on restart —
    # fine for dev, but production (increment 12) MUST set a real one, or
    # every deploy silently logs every parent out.
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_expires_minutes: int = 60 * 24

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def _random_key_if_blank(cls, value: str | None) -> str:
        # JWT_SECRET_KEY= (present but empty) in .env is a distinct case from
        # the var being absent — pydantic-settings takes the empty string
        # literally and default_factory never fires, which would otherwise
        # mean every token gets signed with an empty secret. Belt-and-braces
        # so this stays safe regardless of how .env happens to be formatted.
        return value or secrets.token_urlsafe(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()
