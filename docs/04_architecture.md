# Architecture Design
> PolyInsight v2.0 | 2026-05-17 (최종 업데이트)

---

## 1. 시스템 개요

PolyInsight는 단일 서버에서 실행되는 웹 애플리케이션이다.
사용자가 PDF를 업로드하면 FastAPI 백엔드가 AI 파이프라인(S1~S8)을 비동기로 실행하고,
결과를 SQLite에 저장한다. 프론트엔드(React SPA)는 폴링으로 진행 상태를 확인하고,
카드 에디터에서 수정 후 PNG 내보내기를 트리거한다.

**핵심 설계 원칙**:
- Orchestrator가 파이프라인의 유일한 제어자. 에이전트는 서로 직접 호출하지 않는다.
- 각 스테이지는 검증된 입력을 받고 타입이 정의된 출력을 반환한다.
- S8은 업스트림 실패 여부와 무관하게 항상 실행된다.
- S6는 원문 텍스트만을 사실 근거로 삼는다. 기여 추출은 S6 내부 CoT로 흡수 (S3/S4 제거됨).

**배포 형태 (MVP)**:
- 단일 프로세스 (FastAPI + asyncio)
- Playwright 렌더러: 동일 프로세스 내 비동기 실행
- 프론트엔드: Vite 빌드 → FastAPI static mount 또는 nginx 서빙
- 인프라: 단일 VM (Fly.io 또는 Docker Compose)

---

## 2. 파이프라인 구조

### 2-1. 변경 전 vs 변경 후 비교

| 항목 | v1.0 (이전) | v2.0 (현재) |
|---|---|---|
| S2 Section Parsing | 존재 (regex + LLM fallback) | **제거** — S1이 pymupdf4llm Markdown으로 section_map 직접 생성 |
| S3/S4 Summary/Contributions | 순차 → 병렬 | **제거** — S6 내부 CoT (SEARCH→EXTRACT→WRITE→SCORE→SIGNAL)로 흡수 |
| S5 (홍보 문장) | 존재 | **제거** (KITECH 버전 불필요) |
| S6 사실 근거 | S3/S4 출력 기반 | **원문 section_map 직접 읽기** (CoT 내부에서 기여 추출) |
| S6 레이아웃 결정 | 없음 | **signals 시스템** — LLM이 구조 신호 주석, 코드가 레이아웃 결정 |
| S7 렌더링 엔진 | Pillow (Python 이미지 합성) | **Playwright** (headless Chromium) |
| S7 템플릿 체계 | 없음 | **type_a/b/c/d/e/g/k.html** — layout variant 기반 |
| 저장소 | 인메모리 dict (TTL 30분) | **SQLite** 영구 저장 |
| 파일 보존 | 프로세스 재시작 시 소멸 | PNG/ZIP 24시간 TTL, 메타데이터 영구 |

---

### 2-2. 최신 파이프라인 다이어그램

```
사용자
  │
  │  PDF 업로드
  ▼
[FastAPI]  POST /api/upload
  │
  │  asyncio.create_task()
  ▼
[Orchestrator]
  │
  ├─ S1: Text Extraction      fitz(PyMuPDF) 직접 추출 + pdfplumber fallback
  │        │                   pymupdf4llm Markdown → section_map 직접 생성
  │        │                   PAGE 마커 삽입 (<!-- PAGE N -->)
  │        │  S1Output { raw_text, page_map, section_map, metadata }
  │        ▼                   [S2 제거: S1이 section_map 직접 생성]
  │
  ├─ S6: Card News JSON        원문 section_map 직접 읽기
  │        │                   CoT: SEARCH → EXTRACT → WRITE → SCORE → SIGNAL
  │        │                   LLM이 signals 주석 → 코드가 layout variant 결정
  │        │  S6Output { card_data(CardEditorData), critical_count, high_count }
  │        ▼
  ├─ S7: PNG Rendering         Playwright headless Chromium
  │        │                   layout_variants → type_a/b/c/d/e/g/k.html 선택
  │        │                   1080×1080 × 5장
  │        │  S7Output { images: list[bytes] }
  │        ▼
  └─ S8: Output Packaging      SQLite 저장, ZIP 생성 (항상 실행)
           │
           │  job_id, status = DONE
           ▼
        [SQLite]
           │
           │  폴링 응답
           ▼
        [Frontend]  GET /api/status/:jobId
```

---

### 2-3. 단계별 입출력 명세

| 스테이지 | 입력 | 출력 | 실패 시 |
|---|---|---|---|
| **S1** Text Extraction | `S1Input { job_id, pdf_bytes }` | `S1Output { raw_text, page_map, section_map, metadata, word_count, degraded }` | 파이프라인 중단. S8만 실행 (상태 기록). |
| ~~S2~~ | ~~제거됨~~ | ~~제거됨~~ | S1이 section_map 직접 생성 |
| ~~S3/S4~~ | ~~제거됨~~ | ~~제거됨~~ | S6 내부 CoT로 흡수 |
| **S6** Card News JSON | `S6Input { job_id, section_map, page_map, paper_metadata }` | `S6Output { card_data(CardEditorData), critical_count, high_count }` | 3회 재시도 후 `ERR-S6-001`. 파이프라인 중단. |
| **S7** PNG Rendering | `S7Input { job_id, card_data, theme }` | `S7Output { images: list[bytes], warnings }` | 해당 카드 skip. 부분 성공 허용. |
| **S8** Output Packaging | `S8Input { job_id, card_data, images, warnings }` | `S8Output { job_id, status }` | 항상 실행. 예외 삼킴, status=ERROR 기록. |

**FieldValue 스키마** (S6 출력 단위):

```json
{
  "value": "...",
  "confidence": "high | medium | low",
  "match_quality": "exact | normalized | fuzzy | semantic | failed",
  "claim_type": "quantitative | qualitative | causal",
  "source": { "section": "Results", "page": 7 },
  "risk_level": "CRITICAL | HIGH | MEDIUM | LOW"
}
```

> CRITICAL 조건: `claim_type = quantitative` AND `match_quality = failed`

---

## 3. 컴포넌트 구조

### 3-1. Backend

```
backend/
├── main.py                  FastAPI 앱 진입점, lifespan(migrate+TTL cleaner)
├── agents/
│   ├── base.py              BaseAgent[InputT, OutputT] ABC
│   ├── orchestrator.py      파이프라인 실행 제어 (유일한 컨트롤러)
│   ├── s1_extractor.py      fitz 직접 추출 + pdfplumber fallback, section_map 생성
│   ├── s6_card_json.py      CoT(SEARCH→EXTRACT→WRITE→SCORE→SIGNAL) + layout 결정
│   ├── s7_renderer.py       Playwright PNG 렌더링, variant→type_*.html 선택
│   └── s8_packaging.py      SQLite 저장 + ZIP 생성 (항상 실행)
├── templates/
│   ├── _shared.css          공통 디자인 토큰 (--theme-primary 등)
│   ├── type_a.html          표지형 (Card1, 항상 고정)
│   ├── type_b.html          범용 헤더+카드형 (폴백)
│   ├── type_c.html          수치 강조 그리드형 (stat_count >= 3)
│   ├── type_d.html          before/after 비교형 (has_comparison=true)
│   ├── type_e.html          훅/전면텍스트형 (is_hook=true)
│   ├── type_g.html          플로우형 (has_process_steps, step_count >= 3)
│   └── type_k.html          클로징 (Card5, 항상 고정)
├── api/
│   └── routes/              (Phase 4 미구현)
├── core/
│   ├── models.py            Pydantic 스키마 (Card1~5+Signals, CardEditorData, FieldValue)
│   ├── db.py                SQLite WAL, migrate(), create_job(), update_job() 등
│   └── config.py            pydantic-settings (ANTHROPIC_API_KEY, LLM_MODEL 등)
└── storage/
    └── export_store.py      ExportJobRecord 인메모리 싱글턴
```

### 3-2. Frontend (4개 화면)

```
frontend/src/
├── pages/
│   ├── DashboardPage.jsx    /dashboard — 프로젝트 목록, 통계, 활동 피드
│   └── CardEditorPage.jsx   /editor/:jobId — 3패널 에디터
├── components/
│   ├── dashboard/           대시보드 전용 컴포넌트
│   │   ├── ProjectGrid.jsx
│   │   ├── ProjectCard.jsx
│   │   └── StatsBar.jsx
│   ├── upload/              업로드 모달 (React Portal)
│   │   ├── UploadModal.jsx
│   │   ├── DropZone.jsx
│   │   └── PipelineProgress.jsx
│   ├── editor/              카드 에디터 3패널
│   │   ├── EditorTopBar.jsx
│   │   ├── ContentPanel.jsx
│   │   ├── PreviewPanel.jsx
│   │   ├── DesignPanel.jsx
│   │   └── ActionBar.jsx
│   └── export/              내보내기 모달 (React Portal)
│       ├── ExportModal.jsx
│       ├── PreflightView.jsx
│       ├── RenderingView.jsx
│       ├── DoneView.jsx
│       └── ErrorView.jsx
├── hooks/
│   ├── useCardData.js       카드 데이터 fetch + 자동저장
│   └── usePipelineStatus.js 파이프라인 상태 폴링
├── api/
│   └── client.js            axios 인스턴스 + API 함수 모음
└── types/
    └── cardData.d.ts        TypeScript 타입 정의 (선택)
```

**화면-모달 관계**:
- 업로드 모달 / 내보내기 모달 → `createPortal(…, document.body)` 로 렌더링
- 별도 라우트 없음. 어느 페이지에서도 오버레이로 동작.

### 3-3. Orchestrator 설계

Orchestrator는 파이프라인의 **유일한 진입점**이다.
에이전트는 Orchestrator를 통해서만 호출된다.

```python
# backend/agents/orchestrator.py
async def run_pipeline(job_id: str, pdf_bytes: bytes, theme: CardTheme | None = None) -> None:
    """S1→S6→S7→S8 파이프라인. S8는 항상 실행."""

    # S1 — 블로킹 실패: 예외 시 즉시 종료
    await db.update_job(job_id, status=RUNNING, stage="S1", progress=10)
    s1_out = await s1_agent.execute(S1Input(job_id=job_id, pdf_bytes=pdf_bytes))
    # 실패 시 except에서 ERROR 상태 저장 후 return

    # S6 — LLM 카드 JSON 생성 (3회 재시도, 실패 시 ERR-S6-001)
    await db.update_job(job_id, status=RUNNING, stage="S6", progress=50)
    s6_out = await s6_agent.execute(S6Input(
        job_id=job_id,
        section_map=s1_out.section_map,
        page_map=s1_out.page_map,
        paper_metadata=s1_out.metadata,
    ))

    # S7 — PNG 렌더링 (부분 성공 허용)
    await db.update_job(job_id, status=RUNNING, stage="S7", progress=75)
    s7_out = await s7_agent.execute(S7Input(
        job_id=job_id,
        card_data=s6_out.card_data,
        theme=theme or CardTheme(),
    ))

    # S8 — 항상 실행 (예외 삼킴)
    await s8_agent.execute(S8Input(
        job_id=job_id,
        card_data=s6_out.card_data,
        images=s7_out.images,
        warnings=s6_out.warnings + s7_out.warnings,
    ))
```

각 에이전트는 `BaseAgent[InputT, OutputT]`를 상속하고 `execute(input_data)` 하나만 구현한다.
RunState는 Orchestrator가 직접 `db.update_job()`으로 관리 — 에이전트가 직접 DB를 건드리지 않는다.

---

## 4. 데이터 흐름

```
1. 사용자가 PDF 업로드
   → POST /api/upload
   → SQLite에 job row 생성 (status=PENDING)
   → asyncio.create_task(run_pipeline(job_id, pdf_bytes))
   → 즉시 { jobId } 응답 (202 Accepted)

2. 프론트엔드가 상태 폴링
   → GET /api/status/:jobId (2초 간격)
   → { status, stage, progress, warnings }

3. Orchestrator가 S1~S8 순차/병렬 실행
   → 각 스테이지 완료 시 SQLite job row 업데이트

4. S6 완료 → CardData (FieldValue 스키마) SQLite 저장

5. S7 완료 → png_bytes[] SQLite blob 저장

6. S8 완료 → status=DONE, ZIP 생성, SQLite 업데이트

7. 프론트엔드 폴링에서 DONE 감지
   → /editor/:jobId 이동

8. 사용자가 카드 에디터에서 수정
   → PATCH /api/cards/:jobId (자동저장, 5초 idle)

9. 사용자가 "PNG 내보내기" 클릭
   → POST /api/cards/:jobId/export → { exportJobId }
   → ExportStore에 ExportJob 생성
   → Playwright 비동기 렌더링 시작

10. 프론트엔드가 렌더링 상태 폴링
    → GET /api/export/:exportJobId/status (2초 간격)
    → 카드별 진행 상태 표시

11. 렌더링 완료
    → GET /api/export/:exportJobId/download → ZIP 다운로드
```

---

## 5. 실패 처리 전략

### 5-1. 블로킹 vs 논블로킹 실패

| 스테이지 | 실패 유형 | 파이프라인 영향 |
|---|---|---|
| S1 Text Extraction | **블로킹** | 즉시 중단. ERROR 상태 저장. S8 실행 없이 종료. |
| S6 Card News JSON | **블로킹** (3회 재시도 후) | `ERR-S6-001` raise. Orchestrator가 catch → ERROR 기록. |
| S7 PNG Rendering | **논블로킹** | 카드별 독립. 일부 실패 시 나머지 계속. 부분 ZIP 허용. |
| S8 Output Packaging | **항상 실행** | 예외 삼킴. status=ERROR만 기록. 파이프라인 종료. |

### 5-2. 재시도 정책

| 대상 | 재시도 범위 | 트리거 |
|---|---|---|
| 파이프라인 전체 | S1부터 재실행 | 대시보드 "재시도" 버튼 |
| S6 LLM 호출 | 최대 3회 자동 재시도 | 자동 (ERR-S6-001 후 중단) |
| PNG 렌더링 (S7) | 실패 카드만 재렌더링 | 내보내기 모달 "실패 카드 재시도" |

---

## 6. 저장소 설계

### SQLite 기본 테이블 목록

```sql
-- 파이프라인 실행 단위
CREATE TABLE jobs (
    job_id       TEXT PRIMARY KEY,
    status       TEXT NOT NULL,        -- PENDING|RUNNING|DONE|ERROR
    stage        TEXT,                 -- 현재 실행 중인 스테이지
    progress     INTEGER DEFAULT 0,    -- 0~100
    degraded     INTEGER DEFAULT 0,    -- 1 = degraded_mode
    warnings     TEXT,                 -- JSON array of warning strings
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- S6 출력 (CardData) 저장
CREATE TABLE card_data (
    job_id       TEXT PRIMARY KEY REFERENCES jobs(job_id),
    data_json    TEXT NOT NULL,        -- CardData JSON (FieldValue 스키마)
    updated_at   TEXT NOT NULL
);

-- S7 출력 (PNG bytes) 저장
CREATE TABLE card_images (
    job_id       TEXT NOT NULL REFERENCES jobs(job_id),
    card_num     INTEGER NOT NULL,     -- 1~5
    png_bytes    BLOB,
    size_kb      INTEGER,
    rendered_at  TEXT,
    PRIMARY KEY (job_id, card_num)
);

-- ZIP 패키지
CREATE TABLE exports (
    job_id       TEXT PRIMARY KEY REFERENCES jobs(job_id),
    zip_bytes    BLOB,
    zip_size_kb  INTEGER,
    file_name    TEXT,                 -- kitech_{slug}_{YYYYMM}.zip
    expires_at   TEXT,                 -- created_at + 24h
    created_at   TEXT NOT NULL
);

-- 기관 프로필 (1회 등록, 전체 적용)
CREATE TABLE profile (
    id           INTEGER PRIMARY KEY DEFAULT 1,
    org_name     TEXT,
    logo_bytes   BLOB,
    character_bytes BLOB,
    cta_text     TEXT,
    updated_at   TEXT NOT NULL
);

-- 연구자 사진 라이브러리
CREATE TABLE researchers (
    name         TEXT PRIMARY KEY,
    photo_bytes  BLOB,
    updated_at   TEXT NOT NULL
);
```

**TTL 정책**:
- `card_images.png_bytes`, `exports.zip_bytes` → 24시간 후 NULL 처리 (메타데이터 row는 유지)
- `jobs`, `card_data` → 영구 보존

---

## 7. S6 Signals 시스템

S6는 카드 내용을 생성할 때 **레이아웃 결정용 구조 신호(signals)**를 함께 주석으로 달고,
코드(`_infer_layout()`)가 이를 읽어 layout variant를 결정한다.

### 7-1. signals 스키마

```python
class Card2Signals(BaseModel):
    is_hook: bool = False           # intro가 문제제기/의문/한계면 True

class Card3Signals(BaseModel):
    stat_count: int = 0             # achievement+problem 내 수치 개수
    has_process_steps: bool = False # 실험/제조 단계가 순서 서술이면 True
    step_count: int = 0             # 단계 수

class Card4Signals(BaseModel):
    has_comparison: bool = False    # 기존 vs 신기술 비교 구조 명확하면 True
```

### 7-2. layout variant 선택 규칙

| 카드 | 조건 | variant | 템플릿 |
|---|---|---|---|
| Card1 | 항상 | A | type_a.html |
| Card2 | is_hook=true | E | type_e.html |
| Card2 | is_hook=false | B | type_b.html |
| Card3 | stat_count >= 3 | C | type_c.html |
| Card3 | has_process_steps and step_count >= 3 | G | type_g.html |
| Card3 | 위 조건 미충족 | B | type_b.html |
| Card4 | has_comparison=true | D | type_d.html |
| Card4 | has_comparison=false | B | type_b.html |
| Card5 | 항상 | K | type_k.html |

### 7-3. 설계 근거

LLM은 텍스트 구조 판단에 강하지만 일관성이 없다.
코드는 일관성이 보장되지만 맥락 파악이 약하다.
→ **LLM이 구조 신호를 주석으로 달고, 코드가 규칙으로 variant를 결정**하는 하이브리드 방식.

---

## 8. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|---|---|---|
| 2026-05-17 | v2.1 | S2 제거 (S1이 section_map 직접 생성), S3/S4 제거 (S6 CoT 흡수), signals 시스템 추가, type_* 템플릿 체계 도입, S7 variant 기반 렌더링, 실 API 연결 후 카드 품질 ~60% 향상 확인 |
| 2025-05-05 | v2.0 | S3/S4 병렬화, S5 제거, Playwright 교체, SQLite 도입, FieldValue 스키마 정의 |
| (이전) | v1.0 | 순차 파이프라인 S1~S8, S5 포함, Pillow 렌더링, 인메모리 dict (TTL 30분) |
