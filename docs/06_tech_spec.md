# Tech Spec
> PolyInsight v2.0 | 2025-05-05

---

## 1. 기술 스택 전체

### Backend

| 계층 | 기술 | 버전 | 선택 이유 |
|---|---|---|---|
| 웹 프레임워크 | FastAPI | 0.111+ | async/await 네이티브, Pydantic 통합, 자동 OpenAPI |
| ASGI 서버 | Uvicorn | 0.29+ | FastAPI 표준 런타임 |
| LLM | Anthropic Claude API | claude-sonnet-4-x | 한국어 품질, 128k 컨텍스트, 긴 논문 처리 |
| PDF 추출 | pdfplumber | 0.10+ | 텍스트 레이어 + 좌표 추출. 표/칼럼 처리 우수. |
| PDF 폴백 | PyMuPDF (fitz) | 1.24+ | pdfplumber 실패 시 폴백. 바이너리 속도 우수. |
| PNG 렌더링 | Playwright (Python) | 1.44+ | headless Chromium. HTML/CSS → 픽셀 정확 PNG. |
| 저장소 | SQLite (aiosqlite) | 3.45+ | MVP 단순성. 단일 파일. 추후 PostgreSQL 전환 가능. |
| 유효성 검사 | Pydantic v2 | 2.7+ | 스테이지 입출력 스키마 강제. LLM 응답 파싱. |
| 환경 변수 | python-dotenv | 1.0+ | .env 로드 |
| ZIP 생성 | zipfile (stdlib) | — | 표준 라이브러리. 외부 의존성 없음. |

### Frontend

| 계층 | 기술 | 버전 | 선택 이유 |
|---|---|---|---|
| 프레임워크 | React | 18.3+ | SPA 표준. 팀 친숙도. |
| 빌드 도구 | Vite | 5.2+ | 빠른 HMR. ESM 네이티브. |
| 스타일 | Tailwind CSS | 3.4+ | 유틸리티 클래스. 디자인 토큰 직접 지정. |
| 라우팅 | React Router v6 | 6.23+ | SPA 라우팅. loader/action 패턴. |
| 서버 상태 | TanStack Query (React Query) | 5.40+ | 폴링 추상화, 캐시 무효화, 자동 재시도. |
| HTTP 클라이언트 | Axios | 1.7+ | 인터셉터, 베이스 URL 설정 편의성. |
| 전역 상태 | Zustand | 4.5+ | 경량. 업로드 모달·jobId 등 소수 전역 상태 관리. |
| 포털 | React DOM `createPortal` | (React 내장) | 모달을 document.body에 마운트. |

---

## 2. 주요 기술 결정 및 근거

### 2-1. Pillow → Playwright 교체

**문제**: Pillow는 이미지 합성 방식으로 렌더링하기 때문에 HTML/CSS 레이아웃을 재현할 수 없었다.
복잡한 그리드, 폰트 렌더링, 그림자 등 CSS 속성이 카드 품질에 직접 영향을 주는 상황에서
Pillow로는 디자이너 수준의 출력물을 얻을 수 없었다.

**결정**: Playwright headless Chromium으로 교체. HTML 파일을 브라우저로 열어 스크린샷.

**트레이드오프**:

| 항목 | Pillow | Playwright |
|---|---|---|
| 렌더링 품질 | 이미지 합성 수준 | CSS 완전 지원 |
| 메모리 사용 | 낮음 | 브라우저 프로세스 (~300MB) |
| 설치 복잡도 | pip install | pip install + `playwright install chromium` |
| 렌더링 속도 | 빠름 (~1초/장) | 느림 (~5~15초/장) |
| 서버 요구사항 | 없음 | X 서버 불필요 (headless), 메모리 여유 필요 |

**제약**:
- 카드 1장당 최대 15초 타임아웃 적용
- 5장 전체 최대 25초 (병렬 렌더링 미적용 — 브라우저 메모리 제한)
- Docker 배포 시 `playwright install-deps` 실행 필요

---

### 2-2. 인메모리 dict → SQLite 전환

**문제**: 인메모리 dict는 TTL 30분 만료 시 작업 결과가 소멸했다.
프로세스 재시작 시 모든 데이터 손실. "카드 에디터 이어하기" 기능 구현 불가.

**결정**: SQLite + aiosqlite로 전환. 메타데이터 영구 보존, PNG/ZIP bytes는 24시간 TTL.

**스키마 테이블 목록**:

| 테이블 | 역할 |
|---|---|
| `jobs` | 파이프라인 실행 단위. status, stage, progress, degraded 추적. |
| `card_data` | S6 출력 CardData JSON. 에디터 자동저장 대상. |
| `card_images` | S7 출력 PNG bytes (card_num 1~5). 24h TTL. |
| `exports` | ZIP bytes + 파일명 + 만료일. 24h TTL. |
| `profile` | 기관 프로필 (로고, 캐릭터, CTA). id=1 고정 행. |
| `researchers` | 연구자 사진 라이브러리. name을 PK로 매칭. |

> 전체 DDL → [04_architecture.md § 6. 저장소 설계](./04_architecture.md)

---

### 2-3. S3/S4 병렬 실행

**문제**: v1.0에서 S3(한국어 요약) → S4(핵심 기여)를 순차 실행했으나,
두 스테이지는 동일한 `section_map`을 입력으로 받고 서로의 출력에 의존하지 않는다.
순차 실행 이유가 없었음.

**결정**: `asyncio.gather(s3_summary.run(state), s4_contributions.run(state))` 병렬 전환.

**예상 효과**:
- S3 평균 소요: ~8초, S4 평균 소요: ~6초
- 순차: 14초 → 병렬: 8초 (느린 쪽 기준) → **약 43% 단축**

**주의사항**:
- `return_exceptions=True` 설정 필수 — 한쪽 실패가 다른 쪽을 취소하지 않도록.
- 예외가 반환되면 None으로 처리. S6에서 해당 힌트 미사용.

---

### 2-4. TanStack Query (React Query) 도입

**문제**: 파이프라인 상태 폴링, 내보내기 상태 폴링을 `useEffect + setInterval`로 구현하면
cleanup 누락, 중복 요청, 탭 이동 시 재폴링 등 엣지 케이스 처리가 복잡해진다.

**결정**: TanStack Query의 `refetchInterval` 옵션으로 폴링 통합.

**설정 기준**:

| 쿼리 | `refetchInterval` | `staleTime` | 중단 조건 |
|---|---|---|---|
| 파이프라인 상태 (`/api/status/:jobId`) | 2000ms | 0 | status가 DONE 또는 ERROR |
| 내보내기 상태 (`/api/export/:id/status`) | 2000ms | 0 | status가 done 또는 error |
| 카드 데이터 (`/api/cards/:jobId`) | 폴링 없음 | 5분 | — |
| 대시보드 프로젝트 목록 | 10000ms | 30초 | — |

**효과**:
- 탭 비활성 시 자동 폴링 중단 (`refetchIntervalInBackground: false`)
- DONE 감지 후 자동 폴링 중단 (`enabled: status !== 'DONE'`)
- 캐시 무효화: `queryClient.invalidateQueries(['projects'])` 1회 호출로 목록 갱신

---

## 3. 디렉토리 구조 및 역할

```
polyinsight/
├── backend/
│   ├── main.py                FastAPI 앱 진입점. 라우터 등록, 앱 상태 초기화, 미들웨어.
│   ├── orchestrator.py        파이프라인 유일 제어자. S1→S2→S3/S4→S6→S7→S8.
│   ├── agents/
│   │   ├── s1_extractor.py    PDF 텍스트 추출. pdfplumber 우선, PyMuPDF 폴백.
│   │   ├── s2_parser.py       섹션 분류. regex 우선, LLM 폴백.
│   │   ├── s3_summary.py      한국어 요약. Claude API 호출.
│   │   ├── s4_contributions.py 핵심 기여 추출. Claude API 호출.
│   │   ├── s6_card_json.py    카드뉴스 JSON 생성. 원문 우선. FieldValue 스키마 출력.
│   │   ├── s7_renderer.py     Playwright PNG 렌더링. 카드당 최대 15초.
│   │   └── s8_packaging.py    SQLite 저장, ZIP 생성, 최종 상태 업데이트.
│   ├── api/
│   │   └── routes/
│   │       ├── upload.py      POST /api/upload
│   │       ├── status.py      GET  /api/status/:jobId
│   │       ├── cards.py       GET/PATCH /api/cards/:jobId
│   │       ├── export.py      내보내기 6개 엔드포인트
│   │       ├── projects.py    GET /api/projects, stats, activities
│   │       └── profile.py     GET/POST/PATCH /api/profile
│   ├── core/
│   │   ├── models.py          Pydantic 스키마 (RunState, CardData, FieldValue, 등)
│   │   ├── db.py              SQLite 연결, 마이그레이션, 쿼리 헬퍼.
│   │   └── config.py          환경변수 로드, 상수 (타임아웃, TTL 등).
│   ├── storage/
│   │   └── export_store.py    ExportJob 인메모리 상태. 렌더링 진행 추적용.
│   └── tests/
│       ├── test_s1.py
│       ├── test_s2.py
│       ├── test_s6.py         그라운딩 규칙 검증 우선.
│       └── test_export.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx   /dashboard
│   │   │   └── CardEditorPage.jsx  /editor/:jobId
│   │   ├── components/
│   │   │   ├── dashboard/          프로젝트 그리드, 카드, 통계
│   │   │   ├── upload/             업로드 모달 (React Portal)
│   │   │   ├── editor/             3패널 + TopBar + ActionBar
│   │   │   └── export/             내보내기 모달 (React Portal)
│   │   ├── hooks/
│   │   │   ├── useCardData.js      카드 데이터 fetch + 자동저장 (debounce 5s)
│   │   │   └── usePipelineStatus.js TanStack Query 폴링 래퍼
│   │   ├── api/
│   │   │   └── client.js           axios 인스턴스 + API 함수 전체
│   │   └── types/
│   │       └── cardData.d.ts       CardEditorData, FieldValue TypeScript 타입
│   ├── public/                     정적 자산 (폰트, 로고 등)
│   ├── index.html
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── docs/                           설계 문서 (코드보다 docs가 우선)
├── .claude/                        Claude Code 훅 및 커스텀 명령
├── CLAUDE.md                       실행 프로토콜 (필수 준수)
├── .gitignore
└── README.md
```

---

## 4. 환경 변수

| 변수명 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Claude API 인증 키 |
| `DATABASE_URL` | ✅ | `sqlite:///./polyinsight.db` | SQLite 파일 경로 또는 URL |
| `PLAYWRIGHT_TIMEOUT_MS` | ❌ | `15000` | 카드 1장 렌더링 최대 대기 시간 (ms) |
| `EXPORT_TTL_HOURS` | ❌ | `24` | PNG/ZIP 파일 보존 시간 (시간) |
| `MAX_PDF_SIZE_MB` | ❌ | `50` | 업로드 허용 최대 파일 크기 |
| `LLM_MODEL` | ❌ | `claude-sonnet-4-5` | 사용할 Claude 모델 ID |
| `LLM_MAX_RETRIES` | ❌ | `3` | LLM API 호출 최대 재시도 횟수 |
| `FRONTEND_ORIGIN` | ❌ | `http://localhost:5173` | CORS 허용 오리진 (개발용) |
| `LOG_LEVEL` | ❌ | `INFO` | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) |

> `.env.example` 파일을 레포에 포함. `.env`는 `.gitignore`에서 제외.

---

## 5. 개발 환경 설정

### Backend

```bash
# 1. Python 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. Playwright Chromium 설치 (최초 1회)
playwright install chromium
playwright install-deps chromium   # Linux 서버 환경 필요 시

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 입력

# 5. 개발 서버 실행
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
# 1. 의존성 설치
cd frontend
npm install

# 2. 개발 서버 실행 (Vite proxy → backend :8000)
npm run dev
# → http://localhost:5173

# 3. 프로덕션 빌드
npm run build
# → frontend/dist/ 생성 (FastAPI static mount 또는 nginx 서빙)
```

### Docker (통합 실행)

```bash
# 빌드 및 실행
docker compose up --build

# 서비스 구성:
#   backend  → :8000
#   nginx    → :80 (frontend static + /api proxy)
```

> Playwright를 포함하는 Docker 이미지는 `mcr.microsoft.com/playwright/python` 베이스 이미지 사용 권장.

### 테스트

```bash
# Backend 단위 테스트
cd backend
pytest tests/ -v

# S6 그라운딩 규칙 검증만 실행
pytest tests/test_s6.py -v
```

---

## 6. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|---|---|---|
| 2025-05-05 | v2.0 | Playwright 도입, SQLite 전환, TanStack Query 도입, S3/S4 병렬화, 스택 최신화 |
| (이전) | v1.0 | Pillow 렌더링, 인메모리 dict, useEffect 폴링, 순차 S3→S4 |
