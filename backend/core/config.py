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
    AUTHOR_MAX_TOKENS: int = 32000       # 정교한 아트디렉션 덱도 안 잘리게(streaming으로 호출 → 10분 제한 무관)
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

    # ── CORS (2026-07-02) — 쉼표구분 오리진. 비우면 개발용 로컬만 허용. 프로덕션=터널 도메인. ──
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── 보안 하드닝 (2026-07-02) ──────────────────────────────
    PASSWORD_MAX_LEN: int = 128          # argon2 pre-hash DoS 방지 상한
    RATE_LIMIT_ENABLED: bool = True      # 테스트에서 False
    LOGIN_IP_LIMIT: int = 20             # IP당 로그인 시도(성공 포함) / window
    LOGIN_IP_WINDOW_S: int = 300
    LOGIN_EMAIL_LIMIT: int = 5           # 이메일당 실패 시도 / window (성공 시 리셋)
    LOGIN_EMAIL_WINDOW_S: int = 900
    SIGNUP_IP_LIMIT: int = 5             # IP당 가입 / window
    SIGNUP_IP_WINDOW_S: int = 3600
    PEXELS_API_KEY: str = ""            # 스톡 이미지 검색(선택). 비우면 해당 provider만 skip.
    UNSPLASH_ACCESS_KEY: str = ""        # Unsplash Access Key (Secret Key는 OAuth용, 검색에는 불필요)


settings = Settings()
