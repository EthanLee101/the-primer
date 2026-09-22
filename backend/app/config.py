from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://primer:primer@localhost:5432/primer"
    llm_provider: Literal["gemini", "fake"] = "fake"
    gemini_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
