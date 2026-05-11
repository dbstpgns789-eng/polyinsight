from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "./polyinsight.db"
    LLM_MODEL: str = "claude-sonnet-4-5"
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    EXPORT_TTL_HOURS: int = 24
    MAX_CONCURRENT_JOBS: int = 5
    DEBUG: bool = False

    # Gemini free-tier support (development phase)
    LLM_PROVIDER: Literal["anthropic", "gemini"] = "anthropic"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"


settings = Settings()
