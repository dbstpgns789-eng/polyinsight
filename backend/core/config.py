from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "./polyinsight.db"
    LLM_MODEL: str = "claude-haiku-4-5-20251001"
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    EXPORT_TTL_HOURS: int = 24
    MAX_CONCURRENT_JOBS: int = 5
    DEBUG: bool = False
    DEV_MOCK_LLM: bool = False  # True 시 S6 LLM 호출 없이 mock 데이터 반환


settings = Settings()
