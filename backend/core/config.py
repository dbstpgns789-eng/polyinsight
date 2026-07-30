from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "./polyinsight.db"
    LLM_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_MODEL_ARCHITECT: str = "claude-sonnet-4-6"  # 설계팀(레이아웃 판단) 전용 — 토큰 작아 비용 낮음
    # 헌법 v3.0 단일 저작(Deck Authoring) — 강력한 모델의 현실적 상한 = Opus 4.8.
    # (Fable 5는 thinking always-on으로 토큰 과다 → 비용/속도 부담. Opus 4.8=반값 $5/$25,
    #  thinking 파라미터 생략 시 off라 토큰 효율↑. llm_client가 sampling 파라미터 자동 생략.)
    # 더 저렴하게: "claude-sonnet-4-6"($3/$15). 더 강하게: "claude-fable-5". .env override 가능.
    LLM_MODEL_AUTHOR: str = "claude-opus-4-8"
    AUTHOR_TIMEOUT_S: int = 600          # 대용량 HTML 1회 저작 — 기본 120s로 부족
    AUTHOR_MAX_TOKENS: int = 32000       # 정교한 아트디렉션 덱도 안 잘리게(streaming으로 호출 → 10분 제한 무관)
    # 자연어 편집(nl_patch)은 백지 저작이 아니라 기존 덱 국소 수정 — Opus 불필요. Sonnet으로 속도·비용↓
    # (Opus 편집 실측 ~2.5분/호출 → 편집 UX 붕괴). .env override 가능.
    LLM_MODEL_EDIT: str = "claude-sonnet-4-6"
    # 블랙박스 저지(deck_judge) — 렌더된 카드 PNG를 외부 심사자 루브릭으로 채점(비전).
    # ★sonnet-5는 _NO_SAMPLING_PREFIXES라 temperature 고정 불가 = 저지는 확률적.
    #   점수 비교는 --repeat로 실측한 노이즈 밴드 기준으로만 한다(플랜 Task 4 Step 5).
    LLM_MODEL_JUDGE: str = "claude-sonnet-5"
    # 2000은 실전에서 천장에 닿아 LLMTruncationError 발생(2026-07-12). sonnet-5는 추론 토큰이
    # output에 포함돼 짧은 JSON이어도 총량이 크다. 천장을 올려도 과금은 실사용분만.
    JUDGE_MAX_TOKENS: int = 8000
    AUTHOR_MAX_CARDS: int = 7            # 카드 max 장수(티어로 확장 예정)
    # ⛔ few-shot 레퍼런스(남의 덱 HTML) — **은퇴(2026-07-13)**. 시각 앵커는 논문 자신이다.
    #
    # 유죄: refs의 색 이름·헥스가 산출물에 그대로 복사됨(#36E0CE '전기 시안' → #3DD6D0 '전기 시안').
    #       refs = 소프트 카탈로그. 유한한 레퍼런스로는 '논문 수만큼의 룩'에 도달할 수 없다.
    # 무죄 주장("마감 하한 담보")은 **반증됨**: exp-D-paper-as-ref(refs 0 + 논문 그림 3장)에서
    #       integrity 3→4, dead_zone 해소, 파생수치 오류 0. 마감이 무너지기는커녕 올랐다.
    # 되살리려면 2로. 단 그 전에 AUTHORING.md §4(승격 루프 폐기)를 읽을 것.
    AUTHOR_FEWSHOT_N: int = 0
    # 저작 시 모델에게 보여줄 '이 논문의 그림' 수(비전 입력). 0이면 끔.
    AUTHOR_FIGURES_N: int = 3
    # POLISH: 렌더된 카드를 모델에게 보여주고 시각 결함을 고치게 한다(+1 LLM 콜, 덱당 ~$0.5).
    # 텍스트 자가검수는 무력하다는 실측(5편 전부 '전항 통과' 신고 vs 저지는 5편 전부 결함) 대응.
    # 시각 결함(빈 공간·겹침·형상 오독)은 렌더를 봐야만 잡힌다.
    # ★Best-of-N — 저작 분산을 통제하는 유일한 수단(품질 기능이 아니라 **측정의 전제조건**).
    # Opus 4.8은 sampling 파라미터를 거부해 temperature로 분산을 못 줄인다.
    # 실측(2026-07-13): 같은 논문·같은 코드 5회 저작에서 integrity 2↔4, finish 1~4.
    # n=1 프롬프트 A/B는 노이즈를 읽는 것이다. 유료 티어 = 3.
    AUTHOR_CANDIDATES: int = 1
    AUTHOR_VISION_FIX: bool = True
    # ★2 이상이어야 '루프'다. 1패스면 **수정이 만든 새 결함**을 아무도 못 본다
    # (실측 2026-07-13: 용어 앵커로 텍스트가 길어지자 제목과 수치가 겹침 — finish 4→1).
    # 변경 없이 수렴하면 조기 종료하므로 대개 2콜을 다 쓰지 않는다.
    AUTHOR_VISION_ROUNDS: int = 2
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    WEB_BASE_URL: str = "http://localhost:3000"  # S7 render 라우트 호스트 (Next.js)
    EXPORT_TTL_HOURS: int = 24
    # L1(2026-07-09): 바이너리 파일 저장 루트. 프로덕션은 레포 밖 마운트 볼륨으로 .env override
    # (예: /var/lib/polyinsight/blobstore — 24_system_architecture §4 "호스트 디스크 볼륨").
    STORAGE_DIR: str = "backend/var/blobstore"
    MAX_CONCURRENT_JOBS: int = 5
    DEBUG: bool = False
    DEV_MOCK_LLM: bool = False  # True 시 S6 LLM 호출 없이 mock 데이터 반환
    SESSION_TTL_HOURS: int = 72         # 세션 쿠키/DB 만료
    COOKIE_SECURE: bool = False         # 프로덕션(HTTPS/터널)에서 True
    RENDER_TOKEN: str = ""              # 내부 렌더(Playwright) 서비스 우회 토큰. 프로덕션 필수.

    # ── 스캔본 OCR (2026-07-21) — 텍스트 레이어 없는 PDF 폴백 ──────────
    # 정상 추출(pymupdf4llm)이 단어를 거의 못 뽑으면(=스캔) fitz 내장 Tesseract로 재추출한다.
    # 로컬 Tesseract라 비용 0·서버 밖 안 나감(미발표 논문 안전). 스캔일 때만 발동 → 정상 논문 무영향.
    # ★엔진(Tesseract)은 PyMuPDF에 번들. 필요한 건 언어데이터뿐 → Docker에 tesseract-ocr-kor/eng.
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "kor+eng"       # 국내 학회지(국문)+영문 논문
    OCR_DPI: int = 200                  # 200이 정확도/속도 균형(150은 작은 글자 뭉갬)
    # 페이지 상한 — 스캔 OCR은 페이지당 1~3초라 대용량은 오래 걸린다. 게다가 180k자(Opus 61%)를
    # 넘으면 어차피 source_trim이 중간을 생략한다. 이 지점을 넘는 뒤 페이지는 OCR하지 않고 로그로 알린다.
    OCR_MAX_PAGES: int = 50
    OCR_TESSDATA: str = ""              # 언어데이터 경로. 비우면 TESSDATA_PREFIX 환경변수 사용.

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

    # ── 업로드 쿼터 (유저별 — 재정 DoS·스팸 방어, 2026-07-03) ──
    # 인증 필수 엔드포인트라 user_id 키로 항상 적용(cf-ip 조건 무관).
    # ★쿼터는 원가를 알아야 한다 (2026-07-13 실측: 덱 1건 = $0.51~$3.39, 기본 구성 $1.91).
    # 구 설정(인증 20/일)이면 유저 1명이 하루 $38 — 크레딧 $22가 반나절에 증발한다.
    UPLOAD_USER_LIMIT: int = 5           # 인증 유저 일일 상한 (= 최대 $9.6/일/유저)
    UPLOAD_UNVERIFIED_LIMIT: int = 2     # 미인증은 더 낮게 (= 최대 $3.8/일)
    UPLOAD_USER_WINDOW_S: int = 86400    # 24h
    # ★전역 일일 캡 — 진짜 방어선. 유저 수가 늘어도 하루 총액이 캡된다.
    # 25덱 × $1.91 ≈ $48/일 최악. 0이면 무제한(로컬 개발).
    GLOBAL_DAILY_DECK_LIMIT: int = 25

    # ── 소셜 로그인 OAuth (Google, 2026-07-03) ──────────────────
    # 비우면 dormant(버튼 눌러도 /login 복귀, 앱 안 깨짐). Google Cloud Console에서 발급.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # OAuth 콜백이 등록되는 '브라우저-대면 프론트 오리진'. 비우면 PUBLIC_BASE_URL→WEB_BASE_URL 폴백.
    # dev=http://localhost:3000 (Next rewrite가 /api를 백엔드로 프록시 → 세션쿠키 동일 오리진).
    OAUTH_REDIRECT_BASE: str = ""

    # ── 인스타 자동 발행 (Instagram Login, 2026-07-23) ──────────
    # 비우면 dormant. Meta 앱 크레덴셜 + 토큰 암호화키 + 공개 카드URL 서명키.
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""
    SOCIAL_TOKEN_KEY: str = ""            # Fernet 키(urlsafe base64 32B). 비면 IG 연동 dormant
    PUBLIC_CARD_URL_SECRET: str = ""      # 공개 카드URL HMAC 서명키. 비면 발행 dormant(위조 방지)
    PUBLISH_CREDIT_COST: int = 5          # 발행 1회 크레딧(튜닝값)

    # ── 이메일 인증 (Resend, 2026-07-02) ──────────────────────
    RESEND_API_KEY: str = ""             # 비우면 발송 no-op(dormant). https://resend.com
    EMAIL_FROM: str = "onboarding@resend.dev"   # 도메인 DKIM 검증 전엔 이걸로 본인 메일함 테스트
    EMAIL_FROM_NAME: str = "PaperSweep"
    VERIFY_TOKEN_TTL_HOURS: int = 24
    # 이메일 링크의 사용자-대면 베이스 URL. 비우면 WEB_BASE_URL 폴백(로컬).
    # ⚠️ 프로덕션 필수: WEB_BASE_URL은 내부 렌더 호스트(compose=http://web:3000, 브라우저 접근불가) →
    #    반드시 공개 Cloudflare 터널 도메인으로 설정.
    PUBLIC_BASE_URL: str = ""
    VERIFY_REQUEST_LIMIT: int = 3        # 유저당 인증메일 재요청 / window
    VERIFY_REQUEST_WINDOW_S: int = 900

    # ── 비밀번호 재설정 (2026-07-03) ──────────────────────────
    RESET_TOKEN_TTL_HOURS: int = 2       # verify(24h)보다 짧게 — 비번 변경 권한 토큰
    RESET_REQUEST_LIMIT: int = 3         # 이메일/IP당 재설정 요청 / window
    RESET_REQUEST_WINDOW_S: int = 900
    PEXELS_API_KEY: str = ""            # 스톡 이미지 검색(선택). 비우면 해당 provider만 skip.
    UNSPLASH_ACCESS_KEY: str = ""        # Unsplash Access Key (Secret Key는 OAuth용, 검색에는 불필요)


settings = Settings()
