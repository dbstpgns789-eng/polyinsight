from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "./polyinsight.db"
    LLM_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_MODEL_ARCHITECT: str = "claude-sonnet-4-6"  # 설계팀(레이아웃 판단) 전용 — 토큰 작아 비용 낮음
    # 헌법 v3.0 단일 저작(Deck Authoring) — base tier=Sonnet, premium=Opus(.env로 교체).
    LLM_MODEL_AUTHOR: str = "claude-sonnet-4-6"
    AUTHOR_TIMEOUT_S: int = 600          # 대용량 HTML 1회 저작 — 기본 120s로 부족
    AUTHOR_MAX_TOKENS: int = 16000       # 7장 덱 출력 충분 + 비스트리밍 허용(>10분 streaming 강제 회피)
    AUTHOR_MAX_CARDS: int = 7            # 카드 max 장수(티어로 확장 예정)
    AUTHOR_FEWSHOT_N: int = 2            # few-shot 레퍼런스 수(입력 토큰/비용 트레이드오프)
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    WEB_BASE_URL: str = "http://localhost:3000"  # S7 render 라우트 호스트 (Next.js)
    EXPORT_TTL_HOURS: int = 24
    MAX_CONCURRENT_JOBS: int = 5
    DEBUG: bool = False
    DEV_MOCK_LLM: bool = False  # True 시 S6 LLM 호출 없이 mock 데이터 반환
    SESSION_TTL_HOURS: int = 72         # 세션 쿠키/DB 만료
    COOKIE_SECURE: bool = False         # 프로덕션(HTTPS/터널)에서 True
    RENDER_TOKEN: str = ""              # 내부 렌더(Playwright) 서비스 우회 토큰. 프로덕션 필수.
    PEXELS_API_KEY: str = ""            # 스톡 이미지 검색(선택). 비우면 해당 provider만 skip.
    UNSPLASH_ACCESS_KEY: str = ""        # Unsplash Access Key (Secret Key는 OAuth용, 검색에는 불필요)


settings = Settings()
