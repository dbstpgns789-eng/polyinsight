# Architecture Design
> PolyInsight v2.0 | 2025-05-05

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
- S6는 원문 텍스트만을 사실 근거로 삼는다. LLM 요약(S3/S4)은 힌트 전용.

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
| S3/S4 실행 방식 | 순차 (S3 완료 후 S4) | **병렬** (`asyncio.gather`) |
| S5 (홍보 문장) | 존재 | **제거** (KITECH 버전 불필요) |
| S6 사실 근거 | S3/S4 출력 기반 | **원문 section_map 우선** — S3/S4는 힌트 |
| S7 렌더링 엔진 | Pillow (Python 이미지 합성) | **Playwright** (headless Chromium) |
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
  ├─ S1: Text Extraction      pdfplumber / PyMuPDF
  │        │
  │        │  raw_text, page_map
  │        ▼
  ├─ S2: Section Parsing      regex + LLM fallback
  │        │
  │        │  section_map {title, abstract, methods, results, ...}
  │        ▼
  │     asyncio.gather()
  ├─────┬──────────────────────────┐
  │     │                          │
  │  S3: Korean Summary        S4: Key Contributions
  │  (section_map → KO 요약)   (section_map → 핵심 기여)
  │     │                          │
  │     └──────────┬───────────────┘
  │                │  s3_result, s4_result (힌트)
  │                ▼
  ├─ S6: Card News JSON        원문 direct read + S3/S4 as hints
  │        │                   (S5 없음 — KITECH 버전)
  │        │  card_data (FieldValue 스키마)
  │        ▼
  ├─ S7: PNG Rendering         Playwright headless Chromium
  │        │                   1080×1080 × 5장, 순차 렌더링
  │        │  png_bytes[]
  │        ▼
  └─ S8: Output Packaging      SQLite 저장, ZIP 생성, 상태 업데이트
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
| **S1** Text Extraction | PDF bytes | `raw_text: str`, `page_map: dict` | 파이프라인 중단. ERROR 상태 저장. |
| **S2** Section Parsing | `raw_text` | `section_map: dict[str, SectionText]` | 빈 section_map → degraded_mode 플래그. |
| **S3** Korean Summary | `section_map` | `summary_ko: str`, `confidence: float` | 빈 문자열 반환. S6에서 힌트 미사용. |
| **S4** Key Contributions | `section_map` | `contributions: list[str]` | 빈 리스트 반환. S6에서 힌트 미사용. |
| ~~S5~~ | ~~제거됨~~ | ~~제거됨~~ | — |
| **S6** Card News JSON | `section_map` + `s3_result` + `s4_result` | `CardData` (FieldValue 스키마) | 필드별 `confidence=low`, `risk_level=CRITICAL`. |
| **S7** PNG Rendering | `CardData` + `images` + `profile` | `png_bytes[5]` | 해당 카드 skip. 부분 성공 허용. |
| **S8** Output Packaging | `png_bytes[]` + `CardData` | SQLite row 업데이트, ZIP bytes | 항상 실행. 실패해도 상태만 ERROR로 표기. |

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
├── main.py                  FastAPI 앱 진입점, 라우터 등록, 앱 상태 초기화
├── orchestrator.py          파이프라인 실행 제어 (유일한 컨트롤러)
├── agents/
│   ├── s1_extractor.py      pdfplumber / PyMuPDF 텍스트 추출
│   ├── s2_parser.py         섹션 파싱 (regex + LLM fallback)
│   ├── s3_summary.py        한국어 요약 생성
│   ├── s4_contributions.py  핵심 기여 추출
│   ├── s6_card_json.py      카드뉴스 JSON 생성 (원문 우선)
│   ├── s7_renderer.py       Playwright PNG 렌더링
│   └── s8_packaging.py      SQLite 저장 + ZIP 생성
├── api/
│   └── routes/
│       ├── upload.py        POST /api/upload
│       ├── status.py        GET  /api/status/:jobId
│       ├── cards.py         GET/PATCH /api/cards/:jobId
│       ├── export.py        POST /api/cards/:jobId/export
│       │                    GET  /api/export/:exportId/status
│       │                    GET  /api/export/:exportId/download
│       │                    POST /api/export/:exportId/retry
│       └── result.py        GET  /api/result/:jobId
├── core/
│   ├── models.py            Pydantic 스키마 (RunState, CardData, FieldValue)
│   ├── db.py                SQLite 연결 및 마이그레이션
│   └── config.py            환경변수, 상수
└── storage/
    └── export_store.py      ExportJob 인메모리 상태 (렌더링 진행 추적용)
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
async def run_pipeline(job_id: str, pdf_bytes: bytes):
    state = RunState(job_id=job_id)

    # S1 — 실패 시 즉시 중단
    state = await s1_extractor.run(state, pdf_bytes)
    if state.status == "error":
        await s8_packaging.run(state)
        return

    # S2
    state = await s2_parser.run(state)

    # S3 + S4 병렬
    s3_result, s4_result = await asyncio.gather(
        s3_summary.run(state),
        s4_contributions.run(state),
        return_exceptions=True,
    )
    state.s3_result = s3_result if not isinstance(s3_result, Exception) else None
    state.s4_result = s4_result if not isinstance(s4_result, Exception) else None

    # S6 — 원문 우선, S3/S4는 힌트
    state = await s6_card_json.run(state)

    # S7 — 부분 성공 허용
    state = await s7_renderer.run(state)

    # S8 — 항상 실행
    await s8_packaging.run(state)
```

**RunState**: 파이프라인 전체에서 공유되는 단일 상태 객체.
스테이지는 RunState를 수정하지 않고 새 RunState를 반환한다 (불변 전달 원칙).

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
| S1 Text Extraction | **블로킹** | 즉시 중단. S8만 실행 (상태 기록). |
| S2 Section Parsing | **논블로킹** | degraded_mode=True 플래그. 빈 section_map으로 계속. |
| S3 Korean Summary | **논블로킹** | 예외 포착. None 반환. S6에서 힌트 미사용. |
| S4 Key Contributions | **논블로킹** | 예외 포착. None 반환. S6에서 힌트 미사용. |
| S6 Card News JSON | **논블로킹** | 필드별 CRITICAL 마킹. 빈 카드로 에디터 진입 허용. |
| S7 PNG Rendering | **논블로킹** | 카드별 독립. 일부 실패 시 나머지 계속. 부분 ZIP 허용. |
| S8 Output Packaging | **항상 실행** | 실패해도 상태만 ERROR 기록. 파이프라인 종료. |

### 5-2. 재시도 정책

| 대상 | 재시도 범위 | 트리거 |
|---|---|---|
| 파이프라인 전체 | S1부터 재실행 | 대시보드 "재시도" 버튼 |
| S3/S4 개별 | 해당 스테이지만 재실행 | 자동 (최대 2회) |
| PNG 렌더링 (S7) | 실패 카드만 재렌더링 | 내보내기 모달 "실패 카드 재시도" |
| LLM API 호출 | 지수 백오프 (0.5s, 1s, 2s) | 자동 (최대 3회) |

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

## 7. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|---|---|---|
| 2025-05-05 | v2.0 | S3/S4 병렬화, S5 제거, Playwright 교체, SQLite 도입, FieldValue 스키마 정의 |
| (이전) | v1.0 | 순차 파이프라인 S1~S8, S5 포함, Pillow 렌더링, 인메모리 dict (TTL 30분) |
