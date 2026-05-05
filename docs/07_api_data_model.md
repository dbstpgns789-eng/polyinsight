# API & Data Model
> PolyInsight v2.0 | 2025-05-05

---

## 1. API 엔드포인트 전체 목록

### 1-1. 파이프라인 API

---

#### `POST /api/upload`
PDF를 업로드하고 파이프라인을 백그라운드로 시작한다.

**Request** — `multipart/form-data`
```
file: File   (PDF, 최대 50MB)
```

**Response** `202 Accepted`
```json
{
  "jobId": "uuid-v4",
  "status": "PENDING"
}
```

**에러**: `ERR-INP-001` (PDF 아님), `ERR-INP-002` (50MB 초과), `ERR-INP-003` (텍스트 레이어 없음)

---

#### `GET /api/status/:jobId`
파이프라인 진행 상태를 반환한다. 프론트엔드가 2초 간격으로 폴링.

**Response** `200 OK`
```json
{
  "jobId": "uuid-v4",
  "status": "RUNNING",
  "stage": "S4",
  "progress": 60,
  "degraded": false,
  "warnings": ["S2: abstract section not found, using full text"],
  "updatedAt": "2025-05-05T12:00:00Z"
}
```

`status` 가능 값: `PENDING | RUNNING | DONE | ERROR`

---

#### `GET /api/cards/:jobId`
카드 에디터용 전체 CardEditorData를 반환한다.

**Response** `200 OK`
```json
{
  "jobId": "uuid-v4",
  "cardData": { /* CardEditorData — §2-4 참고 */ },
  "layoutVariants": { "1": "A", "2": "B", "3": "A", "4": "C", "5": "A" },
  "autoSaveStatus": "saved",
  "updatedAt": "2025-05-05T12:00:00Z"
}
```

---

#### `PATCH /api/cards/:jobId/data`
카드 에디터 자동저장. 변경된 필드만 전송.

**Request** `application/json`
```json
{
  "cardData": { /* 부분 CardEditorData */ },
  "layoutVariants": { "1": "B" }
}
```

**Response** `200 OK`
```json
{ "autoSaveStatus": "saved", "updatedAt": "2025-05-05T12:00:05Z" }
```

---

### 1-2. 내보내기 API

---

#### `POST /api/cards/:jobId/export`
PNG 내보내기 작업을 시작한다. Playwright 렌더링을 백그라운드로 실행.

**Request** `application/json`
```json
{
  "cardData": { /* 평탄화된 CardData (plain string 값) */ },
  "images": { "card3": "base64...", "card4": "base64..." }
}
```

**Response** `202 Accepted`
```json
{ "exportJobId": "uuid-v4" }
```

---

#### `GET /api/export/:exportJobId/status`
렌더링 진행 상태를 반환한다. 2초 간격 폴링.

**Response** `200 OK`
```json
{
  "exportJobId": "uuid-v4",
  "status": "rendering",
  "cards": [
    { "card": 1, "status": "done",     "sizeKb": 420 },
    { "card": 2, "status": "rendering","sizeKb": 0 },
    { "card": 3, "status": "pending",  "sizeKb": 0 },
    { "card": 4, "status": "pending",  "sizeKb": 0 },
    { "card": 5, "status": "pending",  "sizeKb": 0 }
  ],
  "totalSizeKb": 420,
  "errorCard": null,
  "errorMessage": null
}
```

`status` 가능 값: `pending | rendering | done | error`

---

#### `GET /api/export/:exportJobId/download`
완료된 전체 ZIP을 다운로드한다.

**Response** `200 OK` — `application/zip`
- `Content-Disposition: attachment; filename="kitech_{slug}_{YYYYMM}.zip"`

**에러**: `ERR-EXP-003` (렌더링 미완료), `ERR-EXP-004` (TTL 만료)

---

#### `GET /api/export/:exportJobId/download/:cardNum`
개별 카드 PNG를 다운로드한다. (`cardNum`: 1~5)

**Response** `200 OK` — `image/png`
- `Content-Disposition: attachment; filename="card_{cardNum}.png"`

---

#### `GET /api/export/:exportJobId/partial`
일부 카드 렌더링 실패 시, 완료된 카드만 묶어 ZIP으로 반환한다.

**Response** `200 OK` — `application/zip`

---

#### `POST /api/export/:exportJobId/retry`
실패한 카드만 재렌더링한다. 완료된 카드는 유지.

**Response** `202 Accepted`
```json
{ "exportJobId": "uuid-v4", "status": "rendering" }
```

---

### 1-3. 프로필 API

---

#### `GET /api/profile`
저장된 기관 프로필을 반환한다.

**Response** `200 OK`
```json
{
  "orgName": "한국생산기술연구원",
  "logoUrl": "/api/profile/logo",
  "characterUrl": "/api/profile/character",
  "ctaText": "연구 문의",
  "updatedAt": "2025-05-05T09:00:00Z"
}
```

---

#### `POST /api/profile`
기관 프로필을 최초 등록한다. (id=1 행 upsert)

**Request** — `multipart/form-data`
```
orgName:   string
ctaText:   string
logo:      File (PNG/JPG)
character: File (PNG)
```

**Response** `201 Created`

---

#### `PATCH /api/profile`
기관 프로필 일부 항목을 수정한다.

**Request** — `multipart/form-data` (변경 항목만 포함)

**Response** `200 OK`

---

### 1-4. 대시보드 API

---

#### `GET /api/projects`
프로젝트 목록을 반환한다.

**Query Params**: `status=done|draft|running|error`, `page=1`, `limit=12`

**Response** `200 OK`
```json
{
  "projects": [
    {
      "jobId": "uuid-v4",
      "title": "나노복합소재 연구",
      "status": "done",
      "thumbnailUrls": ["/api/export/xxx/download/1", "..."],
      "createdAt": "2025-05-05T10:00:00Z",
      "updatedAt": "2025-05-05T11:00:00Z"
    }
  ],
  "total": 42,
  "page": 1
}
```

---

#### `GET /api/projects/stats`
대시보드 통계 카드 4개용 집계 데이터.

**Response** `200 OK`
```json
{
  "total": 42,
  "done": 31,
  "draft": 6,
  "running": 3,
  "error": 2
}
```

---

#### `GET /api/activities`
최근 활동 피드. 최신 20건.

**Response** `200 OK`
```json
{
  "activities": [
    {
      "type": "DONE",
      "jobId": "uuid-v4",
      "title": "나노복합소재 연구",
      "at": "2025-05-05T11:00:00Z"
    }
  ]
}
```

---

### 1-5. 프로젝트 API

---

#### `POST /api/projects/:jobId/retry`
실패한 파이프라인을 S1부터 재실행한다.

**Response** `202 Accepted`
```json
{ "jobId": "uuid-v4", "status": "PENDING" }
```

---

#### `GET /api/projects/:jobId/export/download`
대시보드에서 완료된 프로젝트의 ZIP을 직접 다운로드한다.

**Response** `200 OK` — `application/zip`

**에러**: `ERR-EXP-004` (TTL 만료 — 재렌더링 필요)

---

## 2. 핵심 데이터 모델

### 2-1. Project (SQLite: `jobs` + `card_data`)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `job_id` | TEXT PK | UUID v4 |
| `status` | TEXT | `PENDING\|RUNNING\|DONE\|ERROR` |
| `stage` | TEXT | 현재 실행 중인 스테이지 (`S1`~`S8`) |
| `progress` | INTEGER | 0~100 |
| `degraded` | INTEGER | 0=정상, 1=degraded_mode |
| `warnings` | TEXT | JSON array (경고 메시지 목록) |
| `title` | TEXT | 논문 제목 (S2 파싱 결과) |
| `created_at` | TEXT | ISO 8601 |
| `updated_at` | TEXT | ISO 8601 |

---

### 2-2. ExportJob (인메모리: `ExportStore`)

| 필드 | 타입 | 설명 |
|---|---|---|
| `export_job_id` | str | UUID v4 |
| `job_id` | str | 연결된 파이프라인 job_id |
| `status` | str | `pending\|rendering\|done\|error` |
| `cards` | list[CardStatus] | 카드별 렌더링 상태 |
| `zip_bytes` | bytes\|None | 완료 시 ZIP 데이터 |
| `total_size_kb` | int | 전체 크기 |
| `error_card` | int\|None | 실패한 카드 번호 |
| `error_message` | str\|None | 오류 메시지 |
| `created_at` | datetime | 생성 시각 |
| `expires_at` | datetime | 생성 시각 + 24h |

**CardStatus**:
```python
@dataclass
class CardStatus:
    card: int           # 1~5
    status: str         # pending | rendering | done | error
    size_kb: int = 0
    error_msg: str | None = None
    png_bytes: bytes | None = None
```

---

### 2-3. OrgProfile (SQLite: `profile`)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | INTEGER PK | 항상 1 (단일 행) |
| `org_name` | TEXT | 기관명 |
| `logo_bytes` | BLOB | 로고 이미지 바이너리 |
| `character_bytes` | BLOB | 캐릭터 이미지 바이너리 |
| `cta_text` | TEXT | CTA 문구 |
| `updated_at` | TEXT | ISO 8601 |

---

### 2-4. CardEditorData (프론트 타입)

```typescript
interface CardEditorData {
  meta: {
    org:            FieldValue
    dept:           FieldValue
    researcher:     FieldValue
    month:          FieldValue
    edition_number: FieldValue
  }
  card1: {
    pretitle:      FieldValue
    title:         FieldValue
    mascot_bubble: FieldValue
  }
  card2: {
    intro:        FieldValue
    keyword_line: FieldValue
    footnote:     FieldValue
  }
  card3: {
    problem:       FieldValue
    achievement:   FieldValue
    mascot_bubble: FieldValue
    photo_caption: FieldValue
  }
  card4: {
    before_label:  FieldValue
    after_label:   FieldValue
    description:   FieldValue
    result:        FieldValue
    mascot_bubble: FieldValue
  }
  card5: {
    pre_title:  FieldValue
    main_title: FieldValue
    cta:        FieldValue
    team_name:  FieldValue
  }
  layout_variants: Record<number, 'A' | 'B' | 'C' | 'D'>
}
```

---

### 2-5. FieldValue (신뢰도 스키마)

S6가 출력하는 모든 텍스트 필드의 단위.
프론트엔드는 이 스키마를 기반으로 배지 색상과 "확인 완료" 버튼을 렌더링한다.

```typescript
interface FieldValue {
  value:         string
  confidence:    'high' | 'medium' | 'low'
  match_quality: 'exact' | 'normalized' | 'fuzzy' | 'semantic' | 'failed'
  claim_type:    'quantitative' | 'qualitative' | 'causal'
  source: {
    section: string   // 원문 섹션명 (예: "Results")
    page:    number   // 원문 페이지 번호
  }
  risk_level:    'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  verified:      boolean    // 사용자가 "확인 완료" 클릭 시 true
}
```

**risk_level 판정 기준**:

| risk_level | 조건 |
|---|---|
| `CRITICAL` | `claim_type = quantitative` AND `match_quality = failed` |
| `HIGH` | `match_quality = fuzzy` OR `match_quality = semantic` |
| `MEDIUM` | `match_quality = normalized` |
| `LOW` | `match_quality = exact` OR `claim_type = qualitative` |

**UI 매핑**:

| risk_level | 배지 색 | ActionBar 영향 |
|---|---|---|
| `CRITICAL` | 빨강 | 내보내기 차단 |
| `HIGH` | 주황 | 내보내기 차단 |
| `MEDIUM` | 노랑 | 경고만 표시 |
| `LOW` | 없음 | 영향 없음 |

---

### 2-6. PipelineStatus (폴링 응답)

```typescript
interface PipelineStatus {
  jobId:     string
  status:    'PENDING' | 'RUNNING' | 'DONE' | 'ERROR'
  stage:     'S1' | 'S2' | 'S3' | 'S4' | 'S6' | 'S7' | 'S8' | null
  progress:  number       // 0~100
  degraded:  boolean
  warnings:  string[]
  updatedAt: string       // ISO 8601
}

interface ExportStatus {
  exportJobId:  string
  status:       'pending' | 'rendering' | 'done' | 'error'
  cards: Array<{
    card:       number    // 1~5
    status:     'pending' | 'rendering' | 'done' | 'error'
    sizeKb:     number
    errorMsg:   string | null
  }>
  totalSizeKb:  number
  errorCard:    number | null
  errorMessage: string | null
}
```

---

## 3. 에러 코드 전체 목록

| 코드 | 발생 조건 | HTTP 상태 | 사용자 메시지 |
|---|---|---|---|
| `ERR-INP-001` | PDF 아닌 파일 업로드 | 400 | "PDF 파일만 업로드 가능합니다." |
| `ERR-INP-002` | 파일 크기 50MB 초과 | 400 | "파일 크기가 50MB를 초과합니다." |
| `ERR-INP-003` | 텍스트 레이어 없는 PDF | 422 | "텍스트를 추출할 수 없는 PDF입니다. 스캔본은 지원하지 않습니다." |
| `ERR-S1-001` | pdfplumber + PyMuPDF 모두 실패 | 500 | "PDF 처리 중 오류가 발생했습니다. 다시 시도해 주세요." |
| `ERR-S2-001` | 섹션 파싱 완전 실패 | 200* | — (degraded_mode=true로 계속 진행) |
| `ERR-S6-001` | LLM JSON 파싱 실패 (3회 재시도 후) | 500 | "카드 초안 생성에 실패했습니다. 다시 시도해 주세요." |
| `ERR-LLM-001` | Anthropic API 연결 실패 | 503 | "AI 서비스에 일시적 오류가 발생했습니다. 잠시 후 재시도해 주세요." |
| `ERR-LLM-002` | Anthropic API 레이트 리밋 | 429 | "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요." |
| `ERR-EXP-001` | exportJobId 없음 | 404 | "내보내기 작업을 찾을 수 없습니다." |
| `ERR-EXP-002` | Playwright 렌더링 타임아웃 | 500 | "카드 {N} 렌더링 시간이 초과되었습니다." |
| `ERR-EXP-003` | 렌더링 미완료 상태에서 download 요청 | 409 | "렌더링이 완료되지 않았습니다." |
| `ERR-EXP-004` | TTL 만료 후 download 요청 | 410 | "파일이 만료되었습니다. 다시 내보내기를 실행해 주세요." |
| `ERR-JOB-001` | jobId 없음 | 404 | "프로젝트를 찾을 수 없습니다." |
| `ERR-JOB-002` | RUNNING 중 재시도 요청 | 409 | "이미 처리 중입니다." |
| `ERR-DB-001` | SQLite 쓰기 실패 | 500 | "저장 중 오류가 발생했습니다. 관리자에게 문의하세요." |

> `ERR-S2-001`은 파이프라인을 중단하지 않으므로 HTTP 200 응답 후 status 폴링으로 degraded 상태 확인.

---

## 4. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|---|---|---|
| 2025-05-05 | v2.0 | API 전면 재설계. S5 제거. export API 6개 추가. FieldValue 스키마 확정. 에러 코드 체계화. |
| (이전) | v1.0 | 단순 upload/status/result 3개 엔드포인트. S5 포함. 인메모리 응답. |
