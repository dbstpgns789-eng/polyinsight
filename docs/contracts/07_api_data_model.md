# API & Data Model
> PolyInsight v2.1 | 2026-05-18

---

## 1. API 엔드포인트 전체 목록

### 1-1. 파이프라인 API

---

#### `POST /api/upload`
PDF를 업로드하고 파이프라인을 백그라운드로 시작한다.

**Request** — `multipart/form-data`
```
file:       File     (PDF, 최대 50MB)
card_count: integer  (3~7, 기본값 7) — 생성할 카드 수
                     ※ 상한 7: Haiku 4.5 출력 한계(8192 토큰) 안전권.
                       8장 이상은 큰 논문에서 S6 JSON이 잘림. 등급제 시 상위 모델로 확장.
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
  "stage": "S6",
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
  "updatedAt": "2025-05-05T12:00:00Z"
}
```

---

#### `PATCH /api/cards/:jobId/data`
카드 에디터 자동저장. CardEditorData 전체 교체.

**Request** `application/json`
```json
{
  "cardData": { /* CardEditorData 전체 */ }
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

### 1-6. 이미지 검색 API

---

#### `GET /api/images/search`
무료 스톡 이미지(Pexels + Unsplash)를 검색해 에디터의 "스톡 검색" 탭에 채운다.
백엔드가 키를 보유한 프록시 — 클라이언트에 API 키를 노출하지 않는다.

**Request** — query string
```
q:        string   (필수, 1~200자) — 검색어
per_page: integer  (선택, 1~40, 기본 20)
```

**Response** `200 OK`
```json
{
  "results": [
    {
      "id": "pexels_123",
      "provider": "pexels",
      "url": "https://...",
      "thumb": "https://...",
      "alt": "...",
      "credit": "사진작가명",
      "credit_url": "https://..."
    }
  ]
}
```

**동작 규칙**:
- `PEXELS_API_KEY` / `UNSPLASH_ACCESS_KEY` 둘 다 비어 있으면 `{"results": []}` 반환 (에러 아님 — 업로드만으로 에디터는 정상 동작, degrade-not-fail).
- 한쪽 provider가 실패(레이트리밋·네트워크 오류)해도 다른 쪽 결과는 정상 반환 — provider 단위로 격리.
- `credit`/`credit_url`은 Pexels·Unsplash 라이선스의 저자 표시(attribution) 요건 대응용. 프론트는 표시만 하면 되고, Unsplash의 "다운로드 트리거" 엔드포인트 호출은 아직 미구현(실서비스 트래픽 확대 시 추가 필요 — 알려진 갭).

---

### 1-7. 덱 이미지 자산 API (v3 저작 덱 — 스펙 2026-07-01)

> 저작 덱 HTML(iframe WYSIWYG)에 `<img>` 삽입용 바이트 저장소.
> **설계 심장**: 바이트는 파일시스템(Storage, L1 — `deck_assets.storage_key`가 주소)에, 저장 HTML엔 짧은 URL만.
> 렌더(S7 `deck_renderer`) 직전에만 URL을 DB 바이트→data URI로 인라인한다
> (2MB PATCH 한도 준수 + 쿠키 없는 Playwright 401·set_content base 부재 동시 해소).

#### `POST /api/deck/:jobId/assets`
사용자 업로드 이미지(① 소유진실/② AI 천장 오버라이드/데이터 도표)를 저장한다. `multipart/form-data`.

**Request** — multipart
```
file:        binary  (필수) — 이미지. mime 화이트리스트 = image/png|jpeg|webp|gif (SVG 거부: XSS/SSRF)
source_type: string  (선택, 기본 upload-owned) — upload-owned | upload-data | paper-figure
```
최대 크기 8MB.

**Response** `201 Created`
```json
{ "assetId": "a1b2c3d4e5f6a7b8", "url": "/api/deck/<jobId>/assets/a1b2c3d4e5f6a7b8" }
```
프론트는 반환 `url`을 `insertImage({url, assetId, sourceType})`로 iframe 에이전트에 넘긴다.

**에러**: 잡 없음 404(ERR-JOB-001) · 미지원 mime 400(ERR-IMG-001) · 8MB 초과 400(ERR-IMG-002) · 빈 파일 400(ERR-IMG-003).

#### `GET /api/deck/:jobId/assets/:assetId`
자산 바이트를 원본 mime으로 서빙. **인증 없음 — capability URL**(추측 불가능한 job_id UUID + 16-hex asset_id 조합이 접근 권한). **export/렌더 PNG는 이 라우트를 거치지 않는다**(렌더시 인라인이 대체). 만료/부재 시 404(ERR-IMG-004).

> **왜 무인증인가(스펙 §9 결정 "서빙 라우트 auth는 인라인 전제로 무해화")**: 편집 미리보기는 저작 HTML을 **sandboxed iframe**(`sandbox="allow-scripts"`, 신뢰 경계)에 마운트한다. iframe은 null-origin이라 `<img src="/api/deck/...">` 서브리소스 요청에 SameSite 세션 쿠키가 실리지 않아 인증 서빙은 **401→빈칸 렌더**가 된다(2026-07-01 실측 확인). 렌더 PNG는 인라인이 대체하므로 서빙 라우트는 미리보기 전용 — 무인증 capability URL로 열어 iframe 샌드박스를 유지한 채 미리보기를 살린다. 업로드(POST)는 인증 유지. 자산은 사용자 소유 이미지(로고·사진)로 민감도 낮고, 업로드·덱 접근은 인증 필요(로그인 세션).

**동작 규칙**:
- `data-source-type` 토큰 집합 동결: `stock`(S2 스톡 다운로드-저장) / `upload-owned` / `upload-data` / `paper-figure`. V(충실성)가 읽는 "원문 대조 불가" 신호 = `upload-data` 단일(S3).
- TTL = 덱 수명 정합(기본 720h). 만료 감지 시 프론트에 "이미지 재업로드 필요" 표시.
- degrade-not-fail: 업로드 경로는 스톡 키 유무와 독립. 부분 실패 시 삽입 취소(부분 상태 금지).

#### `<img data-*>` 메타 규약 (HTML이 단일 진실)
이미지 메타는 별도 JSON 스키마가 아니라 삽입된 `<img>`의 속성에 실려 직렬화·DB·export·V까지 보존된다. **`CardSlot` 같은 필드스키마 신설 금지**(헌법 §1 카탈로그 감옥 회피).

| 속성 | 의미 |
|---|---|
| `data-asset-id` | deck_assets PK(assetId) |
| `data-source-type` | stock / upload-owned / upload-data / paper-figure |
| `data-provider` | (스톡) pexels / unsplash |
| `data-credit` / `data-credit-url` | (스톡) 저자 표시 |

> **금지**: `data-pi-artifact`/`data-pi-*` 부착 — editorAgent serialize()가 제거해 소실된다. 메타는 반드시 `data-asset-id`/`data-source-type` 등으로.

#### `POST /api/deck/:jobId/nlpatch/propose` — AI 편집 제안 (미커밋)

자연어/원클릭 지시로 덱 HTML을 **최소 변경 수정한 결과를 미리보기용으로 반환**한다. **저장하지 않고 PNG도 렌더하지 않는다**(유료 LLM 1콜). 사용자가 확인 후 `PATCH /api/deck/:jobId`(commit)로만 반영된다.

**Request** — `application/json`
```json
{
  "instruction": "한 줄로 짧게",
  "html": "<!DOCTYPE html>…",
  "target": { "eid": "eab12cd3", "cardIndex": 2, "quotedText": "현재 요소 텍스트" }
}
```
- `html`: **캔버스 라이브 `serialize()` 결과**(DB의 `deck.html`이 아님). 선택 시 스탬프된 `data-eid`가 이 html에 존재해야 하고, 미저장 직접편집도 여기에 보존된다.
- `target`(선택): 편집 대상 요소 앵커. `eid`는 iframe이 선택 시 부여한 불투명 난수. 있으면 프롬프트가 "이 요소만" 수정하도록 앵커하고, LLM은 `data-eid`를 원형 보존한다.

**Response** `200 OK`
```json
{ "html": "<!DOCTYPE html>…(수정본)", "verify": { "verified": 12, "unverified": 1, "claims": [ … ] } }
```
- `verify`: 수정본을 원문(`paper_text`)과 대조한 결과. 원문 없으면 `{verified:0, unverified:0, claims:[], skipped:true}`.
- **DB·PNG 불변**(저장/렌더는 commit 전용).

**에러**: 잡/덱 없음 404(ERR-JOB-001) · 수정 결과가 카드 구조 이탈(`data-screen-label` 소실) 422(ERR-EDIT-001, 원본 보존).

#### `PATCH /api/deck/:jobId` (commit — 기재 보강)

직접조작 저장과 **AI 제안 적용(commit)** 공용. 요청 `{ "html": "…" }` 저장 → 재검증 + PNG 재렌더. AI 되돌리기는 클라이언트가 commit 직전 html을 스냅샷해 두었다가 이 엔드포인트로 재저장한다(서버는 무상태).

#### `<element data-eid>` — 편집 앵커 규약

iframe editorAgent가 요소 선택 시 부여하는 **불투명 난수 id**(예: `data-eid="eab12cd3"`). 위치·서수 기반이 아니라 요소에 고정된다(MOVE/DELETE/INSERT로 서수가 밀려도 충돌 없음). `data-pi-*`가 아니므로 `serialize()`에서 생존하며 propose·commit·DB까지 보존된다. LLM 편집 시 원형 유지가 강제된다(EDIT_SYSTEM 규칙).

---

### 1-8. 인증 API (플랜 상태)

---

#### `GET /api/auth/me`
로그인한 유저의 계정·플랜 상태를 반환한다. 무료체험 게이트(§2-8 참고)가 프론트 미터·잠금·페이월을 그리는 데 쓴다.

**Response** `200 OK`
```json
{
  "email": "user@example.com",
  "role": "user",
  "emailVerified": true,
  "plan": "free",
  "freeDecksUsed": 0,
  "freeDeckLimit": 1,
  "canAuthor": true,
  "canExport": false,
  "onboarded": false
}
```

---

#### `POST /api/auth/onboarded`
환영 온보딩 시청 완료를 표시한다. 멱등 — 이미 표시됐으면 기존 시각을 유지한 채 그대로 `200`.

**Response** `200 OK`
```json
{ "ok": true }
```

---

## 2. 핵심 데이터 모델

### 2-1. Project (SQLite: `jobs` + `card_data`)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `job_id` | TEXT PK | UUID v4 |
| `status` | TEXT | `PENDING\|RUNNING\|DONE\|ERROR` |
| `stage` | TEXT | 현재 실행 중인 스테이지 (`S1`, `S2`, `S6`, `S7`, `S8`) |
| `progress` | INTEGER | 0~100 |
| `degraded` | INTEGER | 0=정상, 1=degraded_mode |
| `warnings` | TEXT | JSON array (경고 메시지 목록) |
| `title` | TEXT | 논문 제목 (S2 파싱 결과) |
| `created_at` | TEXT | ISO 8601 |
| `updated_at` | TEXT | ISO 8601 |

---

### 2-1a. DeckManifest (SQLite: `deck_manifest`) — v3 저작 지문 (2026-07-11)

저작 콜이 `<!-- PI_MANIFEST {...} -->`로 선언한 편집 결정. 다음 저작 때 최근 3건을 **소프트 변주
선호**로 주입해 계정 단위 동질화를 막는다(모델은 자기가 지난주에 뭘 만들었는지 모른다 —
**다양성은 파이프라인만 가진 정보(이력)에서 나온다**). 계약: `05_agent_design.md §4-A-2`.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `job_id` | TEXT PK | 덱 job |
| `user_id` | INTEGER | 이력 조회 키(계정 단위 변주) |
| `manifest_json` | TEXT | archetype · killer_asset · palette · motif · rejected_arc |
| `created_at` | TEXT | ISO 8601 |

미선언(파싱 실패)은 **경고이지 실패가 아니다** — 그 덱이 이력에 안 남을 뿐(소프트).

---

### 2-1b. DeckAsset (SQLite: `deck_assets`) — v3 덱 이미지 삽입

바이트 원장. 저장 HTML엔 URL만, 렌더시 data URI 인라인(§1-7). PK = `(job_id, asset_id)`.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `asset_id` | TEXT | 16-hex. `(job_id, asset_id)` 복합 PK |
| `job_id` | TEXT | jobs FK |
| `storage_key` | TEXT | L1: 파일 주소 `jobs/{job_id}/assets/{asset_id}`. 바이트는 파일시스템(Storage). `get_deck_asset`가 `dict['bytes']`로 재조립 |
| `mime` | TEXT | image/png\|jpeg\|webp\|gif |
| `source_type` | TEXT | stock\|upload-owned\|upload-data\|paper-figure |
| `source_url` | TEXT? | (스톡) 원본 CDN URL |
| `provider`/`credit`/`credit_url` | TEXT? | (스톡) 저자 표시 |
| `created_at`/`expires_at` | TEXT | ISO 8601. TTL=덱 수명 정합(기본 720h) |

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
// 카드 수가 가변 (card_count에 따라 3~7장)
// 에디터는 cards[] 배열을 순서대로 렌더링
interface CardThemeId = 'forest-light' | 'deep-dark' | 'academic-gray' | 'ivory-soft'

interface CardEditorData {
  recommended_theme: CardThemeId   // S6가 도메인 분석 후 결정. 변경 불가 (읽기 전용)
  user_theme: CardThemeId | null   // 사용자가 RightPanel에서 선택한 값. null이면 recommended_theme 사용
  // 덱 색상 오버라이드 (선택적). 미설정=세트(--set-*) 기본값 사용.
  // 레거시 theme/recommended_theme_key는 스키마 유지하나 신 카드 렌더는 사용하지 않음 (--theme-* 은퇴).
  bg_color?: string       // 덱 배경 오버라이드(선택). --set-bg / --set-bg-gradient를 덮음.
  accent_color?: string   // 덱 강조 오버라이드(선택). --set-accent를 덮음.
  font_pairing?: string   // 덱 글꼴 오버라이드(선택). --set-font를 덮음(레지스트리 키).
  meta: {
    org:            FieldValue
    dept:           FieldValue
    researcher:     FieldValue
    month:          FieldValue
    edition_number: FieldValue
  }
  cards: CardSlot[]
}

interface CardSlot {
  card_num:      number          // 1, 2, 3, ...
  template_type: TemplateType    // 뼈대 종류 — 에디터에서 변경 불가
  fields: Record<string, FieldValue>  // 뼈대별 텍스트 필드 — 에디터에서 value 수정 가능
  image_url?:  string | null     // 이미지 존 보유 뼈대만. 에디터 업로드 시 채움
  focal?:      { x: number; y: number }  // 이미지 초점(0~1). cover 크롭 위치. 없으면 center
  image_fit?:  'cover' | 'contain'       // 존 안 이미지 맞춤. 기본 cover. contain=통째로(잘림0)
  image_mode?: 'box' | 'backdrop' | 'ghost' | 'none'  // 이미지 레이어 배치. S6/Writer가 결정(기본 'box'). 코드엔 이미 존재했으나 문서 누락 — 2026-06-24 반영
  visual_kind?: 'photo' | 'illustration'  // 에셋 종류. 에디터 전용(기본 'photo'). §6.1(docs/18) 참고
  field_styles?: { [fieldKey: string]: FieldStyle }  // 요소별 미세조정(선택적)
}

// 14 레이아웃(skin/skeleton 디자인 시스템, 기본 8 + 확장 6). 상세: docs/18_card_design_system.md
type TemplateType =
  | 'cover_v2' | 'statement' | 'feature' | 'process_v2'
  | 'bigstat_compare' | 'reasons' | 'grid_v2' | 'closing_v2'
  | 'definition' | 'image_hero' | 'callout' | 'multistat' | 'quote' | 'compare_table'

interface FieldStyle {
  size?:    'S' | 'M' | 'L' | 'XL'
  tracking?: number                          // em 단위, [-0.05, +0.1] 클램프
  weight?:  'regular' | 'bold'
  align?:   'left' | 'center' | 'right'
  color?:   'ink-strong' | 'ink-muted' | 'accent'
}
```

**에디터 편집 범위**:
- `fields[*].value` — 텍스트 내용 수정 가능
- `fields[*].verified` — 확인 완료 버튼으로 true 변경 가능
- `image_url` — 이미지 존 보유 뼈대(cover_v2·feature·statement·closing_v2·image_hero)에 업로드
- `focal` / `image_fit` — 이미지 초점(클릭)·맞춤(채움/전체) 조정
- `visual_kind` — 사진/일러스트 전환(RightPanel "에셋 종류"). `illustration`이면 focal 클릭 비활성 +
  backdrop/ghost 배치 옵션 비활성(일러스트는 항상 box 경로). `image_url`과 동일한 신뢰 모델 —
  S6/LLM은 절대 설정하지 않는 에디터 전용 필드(fidelity 불변 유지, docs/18 §6.1).
- `bg_color?: string` — 덱 배경 오버라이드(선택). 미설정=세트 기본. `--set-bg`/`--set-bg-gradient`를 덮음.
- `accent_color?: string` — 덱 강조 오버라이드(선택). 미설정=세트 기본. `--set-accent`를 덮음.
- `font_pairing?: string` — 덱 글꼴 오버라이드(선택). 미설정=세트 기본. `--set-font`를 덮음. 레지스트리 키(`pretendard`·`serif`·`gothic_a1`).
- (레거시 `theme`/`recommended_theme_key`는 스키마 유지하나 신 카드 렌더는 사용하지 않음 — `--theme-*` 은퇴.)
- `field_styles?: { [fieldKey]: FieldStyle }` — 요소별 미세조정(선택적).
  `FieldStyle = { size?: 'S'|'M'|'L'|'XL'; tracking?: number; weight?: 'regular'|'bold';
  align?: 'left'|'center'|'right'; color?: 'ink-strong'|'ink-muted'|'accent' }`.
  전 필드 선택적. 백엔드는 `extra='ignore'`로 통과시키지만, export 메타데이터 보존을 위해
  `CardSlot`에 정식 필드로도 보유한다.
- `template_type` — **변경 불가** (LLM이 결정, 사용자 고정)

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
  jobId:          string
  status:         'PENDING' | 'RUNNING' | 'DONE' | 'ERROR'
  stage:          'S1' | 'S6' | 'S7' | 'S8' | null  // S2~S5 없음 — S1에 흡수 또는 제거
  progress:       number       // 0~100
  degraded:       boolean
  warnings:       string[]     // 유저향 경고 문장
  degrade_events: DegradeEvent[]  // 엔지니어링 텔레메트리(하니스 집계용). warnings와 분리.
  updatedAt:      string       // ISO 8601
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

### 2-7. DegradeEvent (엔지니어링 텔레메트리)

S1Output / S6Output의 `degrade_events: list[DegradeEvent]`는 **엔지니어링/측정 채널**이다.
코퍼스 하니스가 `code`를 GROUP BY해 야생 취약성을 집계한다. 유저향 `warnings`(문장)와 분리.

```typescript
interface DegradeEvent {
  code:    DegradeCode      // 타입드 코드 — 하니스 집계 키
  layout?: string           // S6 카드-로컬일 때만 (template_type)
  detail?: string           // 사람용 부연 — 집계 대상 아님
}

type DegradeCode =
  // S1 soft (파이프라인 계속)
  | 's1_no_sections'        // 섹션 헤딩 검출 실패 → section_map 빔
  | 's1_low_words'          // word_count < 100
  | 's1_parse_fallback'     // pymupdf4llm 실패 → pdfplumber 폴백
  // S1 hard (즉시 중단)
  | 's1_extract_failed'     // 텍스트 추출 자체 불가
  // S6 hard (Mode B 회귀 대상)
  | 's6_coverage_mismatch'
  | 's6_schema_invalid'
  | 's6_truncated'

// HARD_CODES = { s1_extract_failed, s6_coverage_mismatch, s6_schema_invalid, s6_truncated }
// severity는 DegradeEvent 필드가 아니라 코드 분류. 설계: specs/2026-06-25-corpus-robustness-harness-design.md
```

---

### 2-8. User (SQLite: `users`)

계정 + 플랜 상태. `plan`/`free_decks_used`/`onboarded_at`은 무료체험 게이트(2026-07-19, export-gate
순수잠금)를 위해 추가됐다 — §1-8 참고.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | INTEGER PK | AUTOINCREMENT |
| `email` | TEXT | UNIQUE NOT NULL |
| `password_hash` | TEXT | 해시된 비밀번호 |
| `role` | TEXT | 기본값 `user` |
| `email_verified` | INTEGER | 0=미인증, 1=인증 완료 |
| `created_at` | TEXT | ISO 8601 |
| `plan` | TEXT | `free` \| `pro` \| `lab`. 기본값 `free` |
| `free_decks_used` | INTEGER | 무료 체험 소진 카운터. 평생 리셋 없음(월 리셋 없음). 기본값 0 |
| `onboarded_at` | TEXT | ISO 8601. NULL이면 환영 온보딩 미시청 |

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
| `ERR-PLAN-AUTHOR` | 무료 체험 1덱 소진 후 추가 생성 시도 | 402 | "무료 체험 1덱을 모두 사용했어요. 업그레이드하면 계속 만들 수 있어요." |
| `ERR-PLAN-EXPORT` | 무료 플랜에서 파일 내보내기 시도 | 402 | "내보내기는 업그레이드 후 이용할 수 있어요. 만든 카드뉴스는 그대로 보관돼요." |

> `ERR-S2-001`은 파이프라인을 중단하지 않으므로 HTTP 200 응답 후 status 폴링으로 degraded 상태 확인.

---

> **무료체험 게이트 (2026-07-19)** — 무료 = 1덱 "보기 전용". 생성·뷰어·편집·검증 배지는 전부 열려
> 있고(아하 = 검증 완료 배지, 이것은 게이팅 금지), 파일이 실제로 나가는 export 경로만 잠근다.
> 뷰어의 inline 카드 이미지 경로(`/api/cards/{job}/image/{n}`, `/api/deck/{job}/cards/{n}`)는
> 화면 표시용이므로 게이트하지 않는다. 무료 1덱은 업로드 시 선차감하고, 파이프라인이 ERROR로
> 끝나면 환불한다 — 실패로 아하를 못 본 유저가 영구히 막히는 것을 막기 위함.

---

## 4. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|---|---|---|
| 2026-07-19 | v2.7 | 무료체험 export-gate 게이트 계약. `users` 테이블에 `plan`/`free_decks_used`/`onboarded_at` 3컬럼 추가(§2-8 신설). 인증 API 섹션(§1-8) 신설 — `GET /api/auth/me` 응답 확장, `POST /api/auth/onboarded` 신규. 에러 코드에 `ERR-PLAN-AUTHOR`/`ERR-PLAN-EXPORT`(402) 2건 추가. |
| 2026-07-11 | v2.6 | `deck_manifest` 테이블 추가(§2-1a) — 저작 지문(PI_MANIFEST) 저장·반복이력 소프트 주입. `GET /api/deck/:jobId`의 `verify`에 `derived[]`(V2 파생수치 검산: value·kind·suspect·unresolved·verified·context) 추가 — 구 덱엔 없음(optional). |
| 2026-06-24 | v2.5 | `CardSlot.visual_kind?`(사진/일러스트, 에디터 전용) 추가. `image_mode`(기존 코드에 있었으나 문서 누락) 문서화. `TemplateType` 14종 전체 반영(8→14, 드리프트 수정). |
| 2026-06-08 | v2.4 | CardEditorData에 `bg_color?`/`accent_color?` 덱 오버라이드 추가. `--theme-*` 은퇴 명시. 상세: `docs/18_card_design_system.md §3 덱 단위 오버라이드`. |
| 2026-06-03 | v2.3 | card_count 상한 15→7 (Haiku 출력 한계 안전권). S6 LLM 출력에서 risk_level·verified 제외 (코드 자동 판정). LLMTruncationError 도입 — 출력 천장 도달 시 ERR-S6-002 즉시 반환. |
| 2026-06-01 | v2.2 | CardEditorData에 `recommended_theme` / `user_theme` 추가. AI 테마 추천 + 사용자 오버라이드 설계 확정. |
| 2026-05-18 | v2.1 | POST /api/upload에 card_count 추가. CardEditorData → CardSlot 가변 구조. layout_variants 제거. 라우터 구현 완료. |
| 2025-05-05 | v2.0 | API 전면 재설계. S5 제거. export API 6개 추가. FieldValue 스키마 확정. 에러 코드 체계화. |
| (이전) | v1.0 | 단순 upload/status/result 3개 엔드포인트. S5 포함. 인메모리 응답. |
