# ARCHITECTURE.md — 파이프라인 & 시스템 아키텍처

> 코드 계약 문서. 코드와 충돌하면 이 문서가 의도된 설계.
> 자세한 내용: `../docs/contracts/04_architecture.md`, `../docs/contracts/07_api_data_model.md`

---

## 파이프라인 구조 (v2.0)

```
PDF bytes
    ↓
S1  S1Extractor
    - pymupdf4llm → pdfplumber (fallback)
    - section_map: Dict[str, str]
    - page_map: Dict[int, str]
    - degrade_events: List[DegradeEvent]
    ↓
S2  SectionParser (S1 출력 기반 정제)
    ↓
S6  CardNewsAgent
    - section_map + input_profile → Haiku 호출
    - 멀티에이전트: Sonnet(설계팀) + Haiku(콘텐츠팀)
    - 출력: List[CardData] + risk 메타데이터
    ↓
S7  PNGRenderer
    - Playwright → 1080×1080 PNG 스크린샷
    - React 템플릿 기반
    ↓
S8  StorageAgent
    - SQLite 영구 저장 (job + cards + run_state)
    - 항상 실행 (upstream 실패 시에도)
```

---

## Orchestrator 계약

```python
class Orchestrator:
    # 유일한 파이프라인 컨트롤러
    # agent끼리 직접 호출 금지
    async def run(self, job_id: str, pdf_bytes: bytes) -> RunState: ...
```

- 각 stage 결과는 RunState에 누적
- stage 실패 → degrade_events에 기록 → 다음 stage 실행 계속
- S8는 실패 시에도 partial 결과 저장

---

## 핵심 데이터 모델

### RunState

```python
class RunState:
    job_id: str
    status: Literal["pending", "running", "done", "error", "partial"]
    s1_output: S1Output | None
    s6_output: S6Output | None
    s7_output: S7Output | None
    warnings: list[str]
    degrade_events: list[DegradeEvent]
    created_at: datetime
    updated_at: datetime
```

### DegradeCode (enum)

```
S1_EXTRACT_FAILED    — pymupdf4llm + pdfplumber 양쪽 실패
S1_LOW_WORDS         — 추출 텍스트 < 100 words
S1_NO_SECTIONS       — 섹션 헤더 미검출
S1_PARSE_FALLBACK    — pdfplumber fallback 사용
S6_GROUNDING_FAILED  — 원문 grounding 불가
S6_SCHEMA_INVALID    — JSON 스키마 검증 실패
```

### CardData

```python
class CardData:
    card_index: int
    headline: GroundedField
    body: GroundedField
    stat: GroundedField | None
    image_slot: ImageSlot | None
    risk_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

class GroundedField:
    value: str
    confidence: Literal["high", "medium", "low"]
    match_quality: Literal["exact", "normalized", "fuzzy", "semantic", "failed"]
    claim_type: Literal["quantitative", "qualitative", "causal"]
    source: SourceRef   # {section, page}
    risk_level: str
```

---

## DB 스키마 (SQLite)

```sql
CREATE TABLE jobs (
    job_id      TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    pdf_filename TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME
);

CREATE TABLE cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT REFERENCES jobs(job_id),
    card_index  INTEGER,
    card_json   TEXT,       -- CardData JSON
    png_path    TEXT,       -- S7 렌더 결과 경로
    risk_level  TEXT
);

CREATE TABLE run_states (
    job_id      TEXT PRIMARY KEY REFERENCES jobs(job_id),
    state_json  TEXT,       -- RunState JSON
    updated_at  DATETIME
);
```

---

## input_profile

S6 호출 전 논문 프로파일링:
```python
class InputProfile:
    doi: str | None
    journal_family: str      # 저널 패밀리 (DOI prefix 기반)
    columns: int             # 1 or 2 (PDF 컬럼 수)
    estimated_pages: int
    domain: str | None       # 도메인 추정 (agr/chem/med/...)
```

S6 프롬프트 조정에 사용. 2컬럼 저널은 섹션 파싱 전략 다름.

---

## 포트 & 실행

```
FastAPI uvicorn: 포트 8000
개발 실행: uvicorn backend.main:app --reload --port 8000
코드 변경 후: uvicorn 반드시 재시작
```
