from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "./polyinsight.db"
    LLM_MODEL: str = "gemini-2.0-flash"
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    EXPORT_TTL_HOURS: int = 24
    MAX_CONCURRENT_JOBS: int = 5
    DEBUG: bool = False


settings = Settings()
