# 덱 에디터 이미지 삽입 — 통합 구현 설계 (v3 Authoring Pipeline)

> 상태: **설계 승인 완료(2026-07-01)** — 구현 대기. 다음 단계 = writing-plans로 구현 계획 작성.
> 근거: 5개 서브시스템 코드 실측(editorAgent/브리지, S7 렌더·저장, V 검증, 웹 UI, API·데이터모델).
> 관통 제약: 헌법 §1(fidelity over style), v3 Authoring Inversion(카탈로그 감옥 폐기), "최종 판단은 사용자".
> 브랜치: `feat/v3-authoring-pipeline`. 선행: Phase 3a~3f 완료(최신 67ef717).

---

## 0. 이 기능이 왜 존재하나 (브레인스토밍 결론)

저작된 덱은 AI가 스토리+형태+시각자료(SVG 차트·다이어그램)를 한 마음에 저작한다 —
raster 이미지는 **조연**이지 주연이 아니다(예: `output/cardnews_attention` card_04/05는 이미 발행급).
따라서 이미지 삽입의 정당한 자리는 **AI가 저작할 수 없는 것**뿐이다:

- **① 소유된 진실**(AI가 알 수 없음): 기업 로고, 연구실 팀 사진, 현장 사진, 사용자 실데이터, 논문 원본 figure.
- **② AI 천장 오버라이드**: 디자이너가 AI 도표보다 나은 자기 도표를 만들어 교체. 배관은 ①과 동일, UX 진입점만 다름.
- **스톡 배경**: 기존 `/api/images/search`(Pexels+Unsplash) 재사용, 주 용도=배경 분위기.

**핵심 원칙**: 사람 문은 "AI가 못 닿는 곳"에만 연다 → 마법(AI 저작) 0% 희석, 오히려 소유권으로 해자 강화.
응고(coherence)는 **잠금이 아니라 스마트 기본값**으로 지킨다. 감옥 아님.

---

## 1. 범위

### 포함
- 저작 덱 HTML(현재 raster 0장)에 **새 `<img>` 요소 삽입** + 삽입 후 기존 도구(SET_RECT/이동/정렬/리사이즈/페이징)로 **완전 자유 배치**.
- 소스 2갈래: 스톡 검색(재사용) / 사용자 업로드(신설).
- 프리셋 2종: "배경으로"(풀블리드) / "요소로"(바운드 box) — 삽입 시점 인라인 스타일일 뿐, 전부 오버라이드.
- 라운드트립 생존: 삽입 `<img>`가 저장(patchDeck) → V 재검증 → S7 재렌더 PNG → export까지 보존.
- 검증 정직화: 사용자 **데이터 도표만** "사용자 제공·원문 대조 불가" 제3 분류(막지 않음).

### 제외
- 구 고정스키마 에디터(`web/src/components/editor/RightPanel.tsx`)의 `image_mode`(box/backdrop/ghost/none)·CardSlot·CardFrame **데이터 배관** — 신 덱엔 CardFrame이 없다. **UI 마크업만 참고**.
- 이미지 **픽셀 내부** 숫자의 OCR/검증(V는 텍스트 수치만 본다 — 구조적 불가, 시도 안 함).
- 파일시스템 스토리지 + StaticFiles mount 전환(기존 SQLite BLOB 관례 유지 — §4 근거).
- 스톡 크레딧 표기 **강제**(권유만; 별도 슬라이스로 연기 가능).

---

## 2. 아키텍처 (컴포넌트 책임 · 경계)

```
[웹 UI: DeckMediaPanel]  ── 스톡검색 / 업로드 드롭존 / 프리셋 토글 / 데이터도표 체크
   │  onInsert(url, preset, sourceType, meta)
   ▼
[부모 브리지: DeckEditor.tsx]  ── insertImage() 핸들 → postMessage('INSERT_IMAGE')
   │
   ▼
[iframe 에이전트: editorAgent.ts]  ── INSERT_IMAGE = 실제 <img> DOM 삽입(activeCard 내부),
   │                                   undo 커맨드, 프리셋 스타일, 스크림 감지, data-* 부여
   │  getHtml() → serialize()
   ▼
[API: PATCH /api/deck/:id]  ── DeckPatch.html 통째 저장(파싱 없음, max 2,000,000자)
   │
   ├─▶ [V: fidelity.verify_deck]  ── data-source-type="upload-data" 스캔 → 제3 분류
   └─▶ [S7: deck_renderer]  ── 렌더 직전 자산 URL→data URI 인라인 → set_content → PNG(card_images BLOB)

[백엔드 신설: deck_assets 저장소]  ── 업로드/다운로드-저장 바이트 원장 + 서빙 URL
```

**경계 원칙 (단일 진실)**
- **에이전트가 형태를 소유** — 프리셋 기본 위치·크기·z-index·스크림 규칙은 editorAgent가 계산. 부모 브리지는 얇게(명령 전달만). 삽입 대상 카드는 payload가 아니라 에이전트의 `activeCard`가 판단(페이징 단일 진실).
- **HTML이 단일 진실** — 이미지 메타(크레딧/소스타입/asset-id)는 별도 JSON 스키마가 아니라 `<img data-*>` 속성에 실린다. 직렬화에 공짜로 실려 DB·export·V까지 보존. **CardSlot 같은 필드스키마 신설 금지**(§1 카탈로그 감옥 회피).
- **바이트는 deck_assets에, 저장 HTML엔 URL만** — 2MB PATCH 한도 때문에 저장 HTML에 base64 인라인 금지. 인라인은 **렌더 순간에만**.

---

## 3. 핵심 데이터 흐름

### 3.1 삽입 (두 소스)
**스톡**: DeckMediaPanel 검색(`searchStockImages` 기존) → 선택 → **다운로드-저장 프록시** `POST /api/deck/:jobId/assets/from-stock {url, credit, provider, credit_url}` → 백엔드 httpx로 CDN fetch → deck_assets(kind=stock) 저장 → `{assetId, url}` → `onInsert(url, 'background', 'stock', meta)`.

**업로드**: 드롭존 File → `uploadDeckAsset(jobId, file, sourceType)`(api.ts 신설) → `POST /api/deck/:jobId/assets`(multipart) → deck_assets 저장 → `{assetId, url}` → `onInsert(url, preset, sourceType∈{upload-owned|upload-data|paper-figure}, meta)`.

### 3.2 에이전트 삽입 (라운드트립 생존의 핵심)
`editorAgent.ts` INSERT_IMAGE 케이스:
- 대상 = `cardEls()[activeCard]`(현재 보이는 카드만; 숨은 카드 금지). 카드 `position:static`이면 `relative`로.
- `img = document.createElement('img'); img.src = 절대URL; img.style.objectFit='cover'`.
- **`data-pi-artifact` 절대 부착 금지** — serialize()가 `[data-pi-artifact]`,`[data-pi-agent]`를 제거하므로 붙이면 소실. 대신 `data-asset-id` / `data-source-type` / `data-provider` / `data-credit` / `data-credit-url` 부여(제거 대상 아님 → 생존).
- 프리셋 스타일(§5) 적용.
- **undo 보편성 불변식**: DELETE_ELEMENT 역연산으로 `{run: 삽입, undo: 제거}`를 `pushCmd`(redo 비움). 삽입도 되돌리기 가능(3e 불변식).
- `select(img)` → `emitSelected` → `afterMutate`(DIRTY+HEIGHT).
- 스크림 감지: 삽입/드래그-up 후 img 박스가 텍스트리프 형제를 덮으면 부모에 `SCRIM_SUGGEST` post(강제 아님).

### 3.3 저장 → 재검증 → 재렌더
1. `handleSave` → `editorRef.getHtml()` → serialize()가 `<!DOCTYPE html>\n`+outerHTML. **삽입 `<img>`는 data-pi-* 없는 실 DOM이라 생존.**
2. `patchDeck` → `PATCH /api/deck/:id` → `DeckPatch.html`(max 2,000,000자) → `data-screen-label` 존재만 검증 → `persist_edited_deck(job_id, html)`.
3. `persist_edited_deck`: ① paper_text 있으면 `verify_deck(html, paper_text)` 재검증 → ② authored_deck에 html/verify_json/card_count 저장 → ③ `render_deck(html)` 재렌더 → card_images BLOB 덮어쓰기 + `delete_card_images_above`.
4. **렌더 직전 인라인**: `deck_renderer.render_deck`가 `set_content` 전에 HTML 내 `/api/deck/:job/assets/:id` URL을 deck_assets 바이트로 data URI 치환. 이후 `document.images decode` 대기(부분 캡처 방지) → `page.locator("[data-screen-label]").nth(i).screenshot` → PNG.
5. export ZIP: card PNG는 이미지가 래스터로 구워져 자동 포함. deck.html은 URL 참조(오프라인 재현 = §9 열린 질문).

**라운드트립 불변식**: 삽입 `<img data-asset-id>` → serialize 생존 → PATCH 통째 저장 → 재렌더 PNG에 픽셀 존재 → 재편집해도 HTML 유지.

---

## 4. 저장 설계

### 4.1 deck_assets 테이블 (신설) — `backend/core/db.py migrate()`
```
deck_assets(
  asset_id PK, job_id, bytes BLOB, mime TEXT,
  source_type TEXT,        -- stock | upload-owned | upload-data | paper-figure
  source_url TEXT,         -- 스톡 원본 CDN URL(다운로드-저장 시)
  provider/credit/credit_url TEXT nullable,
  created_at, expires_at
)
```
- **card_images의 BLOB+TTL 패턴 재사용**(파일시스템 전무 → 일관성). `save_deck_asset`/`get_deck_asset`/`list`.
- 서빙: `GET /api/deck/:job/assets/:id` → `Response(bytes, media_type=mime)`.

### 4.2 왜 "URL 참조 + 렌더시 인라인"인가 (설계의 심장)
두 제약이 충돌:
- **2MB PATCH 한도**: `DeckPatch.html` max 2,000,000자. 1080px 이미지를 base64로 저장 HTML에 인라인하면 1~2장에 초과 → PATCH 422.
- **렌더러 인증 공백**: `deck.router`는 `get_current_user` 보호. Playwright `set_content`는 쿠키가 없어 authed 자산 URL fetch 시 401 → 이미지가 **빈칸으로 조용히 렌더**(미리보기는 되는데 export PNG엔 누락 = 최악의 파손). 게다가 `set_content`엔 base URL이 없어 상대경로 해결 불가.

**결정**: 저장 HTML은 짧은 URL 참조 유지 + `render_deck`가 set_content 직전에만 자산 URL을 DB 바이트→data URI 인라인.
→ 2MB 한도 준수 + 렌더러가 네트워크/쿠키 없이 self-contained HTML 확보(auth·base 공백 동시 해소) + iframe 미리보기와 export PNG가 **같은 픽셀**로 수렴. 안전망: 인라인 후 `document.images decode` 대기.

### 4.3 스톡: 다운로드-저장 채택 (핫링크 아님)
- 라운드트립 견고성(핫링크는 매 재렌더마다 CDN 재fetch → 만료/rate-limit/30s 타임아웃), 오프라인 export, 업로드와 인라인 배관 통일.
- 트레이드오프: 저장비용 + Pexels/Unsplash ToS(credit 보존) → `source_url`·credit을 deck_assets와 `<img data-credit>`에 기록.
- **SSRF 방지**: from-stock 프록시는 **CDN 호스트 화이트리스트**로 제한. 다운로드는 **라우터 async(httpx)** 에서(렌더 스레드풀 ProactorEventLoop 충돌 회피).

### 4.4 TTL 정합 (결정: 덱 수명과 정합)
card_images/deck_assets 24h vs `authored_deck.html` 무TTL → 덱은 남고 자산만 소멸 시 재렌더에 깨진 이미지.
→ **deck_assets TTL을 덱 수명과 정합(또는 무기한)**. 만료 감지 시 프론트에 "이미지 재업로드 필요" 표시.

---

## 5. 프리셋 → 자유배치 (스마트 기본값, 전부 오버라이드)

프리셋은 **삽입 시점의 인라인 스타일일 뿐**, 코드 필드/스키마 아님(§1). 삽입 후 SET_RECT/이동/정렬/리사이즈로 완전 자유.

### "요소로" (element)
- `position:absolute`, **명시 px** width/height(예 400px + 비율 계산 height). **height:auto 금지** — resize핸들/setRect의 `offsetWidth` 기반 로직이 px를 요구(promoteAll은 이미 absolute인 img에 width/height 안 세팅).
- `left/top` = 카드 중앙 기본.
- 덱 토큰 상속: `border-radius: var(--set-radius, 12px)` 등(정확한 변수명 = §9 열린 질문, 저작 덱 HTML에서 확인).

### "배경으로" (background)
- `position:absolute; inset:0`(1080×1350), `object-fit:cover`.
- **z-index 음수 필수** — 절대배치 img는 같은 스태킹 컨텍스트에서 정적흐름 텍스트 위에 그려진다. 단순 첫 자식 삽입으론 배경 안 됨.
- 3층 조율: `img(z-index:-2)` / `scrim(z-index:-1)` / 텍스트(auto=0).

### 스크림 넛지 (응고 = 잠금 아닌 권유)
- 배경은 거의 항상 텍스트를 덮음 → 삽입 후 `SCRIM_SUGGEST` 배너("배경이 텍스트를 덮나요? 스크림 추가") 원탭.
- `APPLY_SCRIM` 명령 = 실제 직렬화되는 그라디언트 div(z-index img 위·텍스트 아래) 삽입.
- **스크림-이미지 결합**(결정: wrapper div) — img를 wrapper div로 감싸 스크림을 형제로 두고 wrapper 단위 이동/삭제(고아 스크림 방지). 대안 `data-scrim-for=asset-id` 링크.
- 전부 오버라이드 가능. 강제 없음("최종 판단은 사용자").

---

## 6. 충실성 정직화 (해자 일관성)

### 6.1 이미 성립 — 코드 무변경 (긍정 발견)
`fidelity.verify_deck`의 `_content_text`는 `<style>` 제거 → 인라인 style 속성 제거 → **모든 태그 제거**.
`<img alt="...28.4..." src="data:...">`도 태그 전체가 사라져 NumberClaim 0건 → **장식/소유진실 이미지는 자동으로 "조용히" 통과**. 방어코드 선작성 금지(메모리: 실호출에서 배운다).

### 6.2 제3 분류 "사용자 제공 · 원문 대조 불가" (신설)
- **단일 계약 토큰: `data-source-type="upload-data"`** (표기 난립 금지. 미디어삽입·에디터·V·프론트 공유).
- `verify_deck`이 `upload-data` `<img>`(및 사용자 캡션 서브트리)를 스캔 → 그 안 수치를 **verified도 unverified(AI added)도 아닌** 제3 버킷으로. NumberClaim에 `status`(또는 `provenance`) 필드 추가.
- **직렬화 2곳 동시 수정**: `pipeline.py _verify_to_json`(편집 재검증)과 `_execute` 인라인(최초 생성). 한쪽만 고치면 편집 후 라벨 소실. 스키마에 `userProvided:int` + claim별 `status`.
- 프론트(`page.tsx`): VerifyClaim/VerifyData에 상태/카운트 추가. `<aside>`에 amber(AI가 더함)와 **시각적으로 구분되는 중립톤 배지**. **검증됨과 절대 섞지 말 것**(NEVER label verified unless proven).

### 6.3 오검출 방지
- 기본 = 장식(마커 없음, 조용히). "데이터 도표" 체크박스를 켠 업로드만 `upload-data` 부착.
- 라벨 부착점(결정: **이미지 요소 UI 배지 우선**; 데이터 캡션을 쳤을 때만 V 재분류). 배지형이면 V 무변경+프론트만.
- user-provided 서브트리는 `figure/figcaption` 단일 래핑으로 중첩 태그 경계 오인 방지(에디터가 삽입 구조 규정).

---

## 7. 에러 처리 · degrade

| 상황 | 동작 |
|---|---|
| 스톡 키 없음 | images.py 기존 provider skip 유지. 0건이면 패널에 "스톡 사용 불가, 업로드 사용" 안내. 업로드 경로 독립 동작. |
| 업로드 실패(크기·mime) | 서버 mime 화이트리스트(image/*)+최대 크기 → 4xx + 패널 인라인 에러. SVG는 스크립트 제거 또는 거부(XSS/SSRF 축소). |
| 스톡 다운로드 실패 | from-stock 프록시 에러 반환 → 패널 토스트. 저장 안 됨 → 삽입 취소(부분 상태 금지). |
| 렌더 시 이미지 못 불러옴 | **인라인 전처리로 근본 회피.** 인라인 실패 시 해당 img를 플레이스홀더로 두고 렌더 계속(카드 전체 실패 방지) + 로그. |
| 자산 TTL 만료 후 재편집 | TTL 덱 수명 정합(§4.4). 만료 감지 시 "이미지 재업로드 필요" 표시. |
| networkidle이 디코드 미보장 | `document.images decode` 대기 안전망으로 부분 캡처 방지. |

원칙: **막지 않고 degrade + 표면화**. 조용한 실패(빈칸 렌더) 절대 금지.

---

## 8. 테스트 계획

### 라운드트립 불변식 (핵심)
1. **삽입→저장→재렌더 PNG에 이미지 존재**: 자산 삽입 → getHtml → persist_edited_deck → 재렌더 PNG가 순수 배경과 **픽셀 차이**(data URI 인라인 경로 포함).
2. **직렬화 보존**: 삽입 `<img data-asset-id data-source-type>`가 serialize 결과 HTML에 존재(data-pi-* 제거에 안 걸림). 왕복 후 속성 유지.
3. **undo 보편성**: 삽입 직후 undo → img 제거, redo → 복원(3e 불변식 회귀).
4. **페이징 대상**: activeCard가 아닌 카드에 삽입 안 됨(cardEls()[activeCard] 한정).

### V 회귀 (`backend/tests/test_deck_pipeline.py`)
5. `upload-data` 마킹 캡션 수치 → 제3분류. 마커 없는 캡션 → 기존 대조. (`test_verify_deck_classifies_provenance`)
6. 직렬화 2경로(_verify_to_json / _execute) 스키마 동일성 — 편집 후 라벨 소실 없음.

### 프리셋/스타일 · degrade
7. 배경 프리셋 z-index 3층 페인트 순서(텍스트가 이미지 위) — 실브라우저 하네스.
8. element 프리셋 명시 px width/height → resize핸들 정상.
9. 스톡 키 없음 → 검색 degrade, 업로드 독립. 렌더 인라인 실패 → 카드 전체 실패 안 함.

경량 하네스(31체크 방식) + 풀스택 실브라우저 Stage1/2 패턴 재사용(3e 자산). 테스트: `pytest backend/tests/`.

---

## 9. docs 먼저 갱신 (헌법 §4: docs→code) + 결정

### docs 갱신 (코드 착수 전)
- `docs/contracts/07_api_data_model.md`: `POST /api/deck/:job/assets`(multipart), `POST /api/deck/:job/assets/from-stock`, `GET /api/deck/:job/assets/:id` 계약 + `deck_assets` 테이블 + **`<img data-*>` 메타 규약**.
- `docs/contracts/18_card_design_system.md`: 신 덱 삽입 프리셋("배경으로"/"요소로")과 구 `image_mode`(신 덱 미적용) 관계 명시.
- (선택) `docs/contracts/12_card_editor_content.md`: 미디어 삽입 섹션 UX.

### 결정 완료 (기본값 — 필요 시 재검토)
- 자산 서빙: **렌더시 data URI 인라인** 채택(서빙 라우트 auth 정책은 인라인 전제로 무해화).
- `data-source-type` 토큰 집합 동결: `stock` / `upload-owned` / `upload-data` / `paper-figure`. V가 읽는 "대조 불가" 신호 = `upload-data` 단일.
- "대조 불가" 라벨 부착점: **이미지 요소 UI 배지 우선**(캡션 수치 있을 때만 V 재분류).
- 스크림-이미지 결합: **wrapper div**.
- deck_assets TTL: **덱 수명 정합**.
- export ZIP: 원본 assets/ 폴더 **동봉**(소유진실 재사용).
- 배경 자동 스크림: **감지 후 권유만**(항상 자동 아님).

### 남은 열린 질문
- 덱 토큰 변수명(`--set-radius` 등) 저작 덱 HTML에서 실측 확인.
- ② AI 천장 오버라이드에서 교체된 원 AI 도표의 verified claim이 HTML 제거로 자동 재검증에 반영되는지 확인(라운드트립상 무해 예상).

---

## 10. 서브슬라이스 순서 (라운드트립 최소 증명 우선)

**S0 — 라운드트립 골격 (하드코딩 이미지로 픽셀 증명)**
- `deck_renderer` 자산 URL→data URI 인라인 전처리 + `document.images decode` 대기.
- editorAgent `INSERT_IMAGE`(element 프리셋만, undo 포함) + DeckEditor 핸들.
- 임시 고정 URL 하나로 삽입 → getHtml → persist → 재렌더 PNG 픽셀 diff 테스트(불변식 #1·#2·#3).
- **이 단계에서 auth 공백·base URL 공백·직렬화 생존·페인트순서·decode 대기·2MB 한도 = 6대 리스크를 한 번에 검증.**

**S1 — 업로드 저장소 (① 소유진실 배관)**
- deck_assets 테이블 + `POST /api/deck/:job/assets` + `GET .../assets/:id` + api.ts `uploadDeckAsset`.
- DeckMediaPanel 업로드 드롭존 → 실제 업로드 URL로 S0 경로 구동. mime/크기 검증.

**S2 — 스톡 배경 (다운로드-저장)**
- `POST .../assets/from-stock`(CDN 화이트리스트) + DeckMediaPanel 스톡검색 이식(RightPanel 참고) + background 프리셋(z-index 3층) + 스크림 넛지.

**S3 — 검증 정직화 (② 천장 오버라이드 + 데이터도표)**
- `upload-data` 체크박스 → data-source-type → verify_deck 제3분류(2경로 스키마) → 프론트 중립 배지. V 회귀 #5·#6.

**S4 — 마감**
- SELECTED에 isImage 분기(이미지 선택 시 스크림/데이터도표 컨트롤), export 인라인본 결정, TTL 정합, docs 최종 동기화.

> S0 통과 = 라운드트립 6대 리스크가 실증적으로 닫힘. 이후 S1~S4는 소스·UX를 붙이는 저위험 증분.

---

## 관통 리스크 요약 (구현 시 상시 참조)
- **저장 HTML에 base64 인라인 금지**(2MB 한도) → URL 참조 + 렌더시 인라인.
- **Playwright 쿠키 없음** → authed 자산 URL 401 조용한 실패 → 렌더시 인라인으로 회피.
- **`data-pi-artifact` 부착 금지**(serialize가 제거) → 메타는 `data-asset-id`/`data-source-type`로.
- **배경은 z-index 음수 3층** 아니면 텍스트를 덮음.
- **element 프리셋 `height:auto` 금지**(offsetWidth 기반 로직 붕괴).
- **삽입은 activeCard 한정**(숨은 카드 금지).
- **스톡 다운로드는 라우터 async httpx**(렌더 스레드풀 충돌 회피).
- **구 RightPanel은 UI만 참고** — onImageUpdate(슬롯 교체) 배관 이식 금지, onInsert(새 요소)로 재정의.
