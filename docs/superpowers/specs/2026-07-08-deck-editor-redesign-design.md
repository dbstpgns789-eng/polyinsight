# /deck/[jobId] 뷰·편집 리디자인 — 설계 (Design Spec, rev2)

- 날짜: 2026-07-08 (rev2 — 5-렌즈 리뷰 blocker 14/major 23 반영 전면 개정)
- 대상: `web/src/app/deck/[jobId]/` 뷰·편집 (앱 크롬) + 이를 지탱하는 **백엔드 계약·editorAgent 확장**
- 상태: 재리뷰 대기

> **rev2 개정 요지**: rev1은 UX만 설계하고 이를 지탱할 계약(AI 편집 propose/commit·요소 타겟팅·editorAgent 확장·되돌리기)을 "확장" 한 단어로 감췄다. 리뷰가 이를 blocker로 잡음. rev2는 그 계약을 **스코프 안으로 끌어와 명세**하고, 진짜 불변 자산을 바로잡고, 실현 불가한 약속(도형/펜 도구·팩트 출처 카피)을 축소·강등하며, **4개 서브프로젝트로 분해**한다.

---

## 1. 목표

연구원(디자이너 툴 비숙련)을 위해 **AI로 편하게 고치는 것을 주(主)** 편집 수단으로. 전문 인스펙터는 보조. dc.html `isEditor` 레이아웃·모션 채택, **팔레트는 forest-green 유지**.

## 2. 스코프

**포함**
- 편집 화면 재설계 (상단바·좌 도구·중앙 캔버스·우 탭)
- **AI 도우미 + 이를 위한 백엔드/iframe 계약** (propose/commit·요소 target·되돌리기 — §4.2)
- 직접 편집 인스펙터 (보조 — 1차는 현 SELECTED 필드 범위)
- 뷰 화면 (큰 카드 + 썸네일 + 바로 편집)
- 팩트 체크 UX (적응형 배지)
- Export modal (v3 덱용, 소프트 경고)
- **필요한 계약 변경**: `nlpatch` propose/commit·target 필드(`docs/contracts/07_api_data_model.md` 갱신 선행), editorAgent SELECTED 페이로드 + 안정 요소 id, `patchDeck` render 분리 옵션.

**제외 (defer / 별도 스펙)**
- **도형·원·선·화살표·펜·차트·신규 텍스트박스 삽입 도구** — editorAgent에 삽입 명령이 없음(현재 `INSERT_IMAGE`만). 별도 스펙(Phase 3f급). 1차 좌측 도구 = **선택 · 이미지 · (기존 텍스트 편집)**만.
- 인스펙터 확장 필드(자간·줄간격·모서리·투명도·그림자·회전) **읽기** — styleSnapshot 확장 필요, 1차 제외(§4.3).
- 멀티포맷·발행예약·애널리틱스, 팔레트 재브랜딩(바이올렛), legacy `/editor`·`/render`.

## 3. 하드 제약 (변경 불가)

1. **forest-green 단색** — accent = `var(--accent)`(oklch 52% 0.15 163). @theme에 hex/rgb 금지, 토큰 경유. 화려한 그라디언트 배경·파스텔·포인트컬러 2개+ 금지(cdo/DESIGN_SYSTEM.md).
2. **다크 배경은 auth/CTA 한정** — 편집기 사이드바/툴바/상단바는 **라이트**. 다크 사이드바(dc.html 이식) 금지.
3. **토큰 네임스페이스** — 앱 크롬 `--*` ↔ 카드 `--set-*` 혼용 금지.
4. **진짜 불변 공유 자산**(rev1의 "CardRenderer 불변"은 오지목 — v3 캔버스는 CardRenderer를 안 쓰고 저작 HTML을 srcDoc 직접 마운트):
   - **저작 HTML 구조**(`data-screen-label` 카드 경계) 불변 — 편집 캔버스와 발행 PNG(`deck_renderer.py` `page.set_content` 직접 렌더)가 같은 HTML 소비.
   - **editorAgent 직렬화 계약**(`serialize()`: 편집 아티팩트 제거 후 클린 HTML) 불변 — 저장/렌더가 이에 의존.
   - editorAgent **명령·SELECTED 페이로드는 확장 허용**(§4.2·§4.3이 요구). 단 직렬화 산출물은 원본 저작 HTML과 호환 유지.
5. **Export = modal(React Portal), 소프트 경고**(하드블록 금지).
6. **`@layer base` 리셋**, **이식 전 토큰 매핑 테이블 필수**, 완료 기준 = 시각 검증.

## 4. 화면 설계

### 4.1 편집 레이아웃

```
상단바: P PolyInsight  파일명.deck  ↶ ↷   ● 저장됨  [내보내기]
├ 좌 도구(세로): 선택 · 이미지 · (텍스트 편집)   ← 1차. 도형/펜/차트는 defer
├ 중앙 캔버스: DeckEditor(iframe) — 카드 네비 ‹n/7› + 선택 핸들
└ 우 패널(탭): [AI 도우미] · [직접 편집] · [팩트 체크]
```

- **상단바**: 로고 락업 · 파일명(mono) · undo/redo · 저장 상태 · 내보내기(→ Export modal §4.6).
- **좌측 도구(1차 축소)**: 선택 / 이미지(드롭존, 현 DeckMediaPanel 흡수) / 기존 텍스트 편집(캔버스 contenteditable). **도형·원·선·펜·차트·신규 텍스트박스는 defer** — editorAgent 삽입 명령이 `INSERT_IMAGE`뿐이라 1차 스코프에서 제외(§2). "AI 중심·연구원" 논지와도 정합(드로잉 도구 불필요).
- **중앙 캔버스**: `DeckEditor`(iframe) 유지. iframe **내부 CardRenderer 없음**(저작 HTML srcDoc). editorAgent는 §4.2·§4.3 위해 **명령·SELECTED 확장**(제약 4 허용 범위).
- **우 패널 탭**: 기본 = AI 도우미. 요소 선택 시 AI 도우미 맥락 갱신(탭 자동전환 안 함).

### 4.2 AI 도우미 (핵심 — 계약 명세)

**흐름**: 요소 선택 → 제안 대기 → (원클릭 or 자연어) → **AI 제안(미커밋)** → before/after → [✓ 적용] / [↻ 다른 안] / [✕].

이를 위해 **propose/commit 2단 + 요소 target**을 신설한다(rev1의 "nlPatchDeck 확장" 구체화):

- **요소 타겟팅**
  - editorAgent가 선택 시 요소에 **안정 id를 스탬프**(`data-eid` — `data-pi-*`가 아니어야 `serialize` 생존, 현 `serialize`는 `data-pi-*`만 제거). **id는 불투명 난수를 1회 생성해 요소에 고정**(위치·서수 기반 아님 — MOVE/DELETE/INSERT로 서수가 밀려 충돌하므로).
  - `SELECTED` 페이로드에 `{ eid, cardIndex, tag, quotedText(전체, 절단 상향) }` 추가.
  - 프론트가 propose 요청에 `target: { eid, cardIndex, quotedText }`를 실어 프롬프트에 "이 요소만" 앵커.
- **propose (미커밋, 유료 1콜)** — 신규 `POST /deck/{id}/nlpatch/propose` (또는 `nlpatch`에 `persist=false`)
  - 입력: `{ instruction, target, html }` — **html은 캔버스 라이브 `serialize()` 결과**(DB `deck["html"]`가 아님). 이래야 선택 시 스탬프한 `data-eid`가 대상 html에 존재하고 **미저장 직접편집도 보존**된다(현 nlpatch는 DB html을 써서 둘 다 누락). 출력: `{ html, verify }`. **DB 저장·PNG 렌더 안 함.**
  - 원클릭 제안(한 줄로·크게·쉽게·색)도 각각 1콜(비용 고지). **[↻ 다른 안] = propose 재호출(추가 1콜)**.
- **commit (적용)** — 기존 `PATCH /deck/{id}`(`patchDeck`) 재사용: propose된 html을 저장 → 재검증 + PNG 렌더. **[✓ 적용] 시에만.**
- **취소 [✕]** — 서버 무변(propose 미저장). 프론트 pending proposal 폐기.
- **before/after**: 백엔드에 HTML 파서가 없으므로(fidelity=regex only) **프론트에서 target 요소의 이전/이후 텍스트를 DOM 비교**해 표시. EDIT_SYSTEM에 **`data-eid` 원형 보존 규칙**을 추가해 전체 재작성 LLM이 편집 요소의 eid를 떨구지 않게 한다(after 매칭 보장).
- **되돌리기(§ AI 편집 이력)**: 전역 undo(iframe 커맨드)와 **별개**. AI commit은 iframe 재마운트로 커맨드 스택을 지우므로, **부모(React)가 commit 직전 html을 스냅샷 스택에 push** → "되돌리기" = 스냅샷을 `patchDeck`으로 재저장(재검증+PNG 재렌더, "되돌리는 중…" 표기). 상단바 undo/redo는 직접조작(iframe)용, AI 되돌리기는 스냅샷용 — UI에서 분리 표기.
- **1차 제안 세트**(요소 종류별, 구현 근거):
  - 텍스트(제목/본문): `한 줄로 짧게`(줄 수 힌트는 SELECTED rect/줄바꿈으로 근사), `더 크게`, `더 쉬운 말로`, `색 바꾸기`.
  - 이미지: `교체`, `크기 맞추기`.
  - (도형/차트 없음 — defer.)

### 4.3 직접 편집 인스펙터 (보조 탭, 1차 범위)

현 `SelectedInfo.styles`(color/fontSize/textAlign/fontWeight/background)로 **읽기·쓰기 되는 필드만** 1차. Image #7식 시각(섹션 그룹·인라인 필드)은 이 범위에서.

- **1차**: 글자색 · 크기 · 정렬 · 굵기 · 배경 + 위치/크기(`SET_RECT`) + 순서·삭제·`↺ 흐름 복귀`(`REVERT_FLOW`)·다중 정렬/분배.
- **확장(defer)**: 자간·줄간격·모서리·투명도·그림자·회전 — **읽기(현재값 표시)**가 `styleSnapshot` 확장을 요하므로 별도. 쓰기는 `APPLY_STYLE`로 가능하나 현재값 미표시는 UX 저하 → 1차 제외.
- 기존 `DeckElementPanel` 계약(`SelectedInfo`·`applyStyle`·`setRect`·`revertFlow`·`align`·`distribute`) 재구성. 직접조작(드래그/리사이즈/핸들) 불변.

### 4.4 뷰(완성 덱 보기) — "한 장씩 + 썸네일"

- 상단바(편집과 통일) · 팩트 배지(§4.5) · 내보내기.
- 큰 카드 1장 + 좌우 네비 + 썸네일 스트립(전체 조망·클릭 전환·키보드 ←/→).
- **"이 카드 편집"** → 편집 모드로 **그 카드 index로 진입**(`SET_PAGE` 핸드셰이크: 뷰의 현재 index를 편집 마운트 시 전달).
- **엣지**: PNG 렌더 미완/실패 → 카드·썸네일에 "그리는 중…"/재시도(빈 화면 금지). 카드 0장/1장 덱 상태 정의(네비·스트립 숨김).

### 4.5 팩트 체크 (적응형, 카피 강등)

"충실성 검증·해자" 폐기 → **"팩트 체크"**. **verify 데이터는 `{value, context, verified}`뿐 — 섹션·페이지 없음.**

- **배지(뷰·편집 공통)**: 확인 필요 0 → 초록 `✓ 수치 N 확인`; ≥1 → 주황 `⚠ N개 확인 필요`(클릭 → 상세).
- **상세**: 부제 "원문에 없는 수치는 따로 표시해요." + 스탯(확인 N / 확인 필요 N) + 항목: `값` + 배지(`원문에서 찾음` green / `원문에 없음` amber) + **context 스니펫 인용**(있는 데이터).
  - ⚠️ **금지**: "Results, p.7", "정확히 일치" 등 코드가 증명 못 하는 출처·정합 주장(헌법 `NEVER label verified unless code proves it`). 위치 표기가 필요하면 `fidelity.py` 매치 오프셋→섹션 추정을 **별도 백엔드 작업**으로(이 스펙 밖).
- **상태**: 재검증 불가(`canReverify=false`·원문 없음) → "재검증 안 됨" 안내(막지 않음). N 카운트는 `verify.claims`에서 `verified` 집계(프론트).

### 4.6 Export modal

- 내보내기 → **modal**(React Portal). 기존 `ExportModal`은 legacy(`/editor`, `Card.fields[].risk_level`·uiStore 결합)라 **v3 덱용 신규/어댑테이션**.
- **소프트 경고**: `verify.unverified ≥ 1`이면 "확인 필요한 수치가 있어요" 경고 표시, **그래도 내보내기 가능**(하드블록 없음). 데이터는 `getDeck` 응답에 이미 있음.

## 5. 컴포넌트 · 계약 변경

| 대상 | 변경 |
|---|---|
| `deck/[jobId]/page.tsx` | 뷰/편집 레이아웃 재구성 + AI 스냅샷 스택 상태 + 뷰↔편집 index 핸드셰이크. |
| `DeckEditor.tsx` / `editorAgent.ts` | **SELECTED에 `{eid, cardIndex, quotedText}` 추가 + 선택 시 `data-eid` 스탬프**(serialize 생존). 직렬화 산출물 원본 호환 유지. |
| `DeckNLBar.tsx` | → `DeckAIAssistant` (맥락·제안·propose/before-after·commit·다른안·스냅샷 되돌리기). |
| `DeckElementPanel.tsx` | → `DeckInspector`(1차 필드 범위, §4.3). |
| `DeckMediaPanel.tsx` | → 좌측 이미지 도구. |
| **백엔드** | `nlpatch` **propose(persist=false, `{html,verify,change}`) 신설** + `DeckNLPatch`에 `target` 필드. `docs/contracts/07_api_data_model.md` **갱신 선행**(docs-first). |
| (신규 FE) | `DeckTopBar`, `DeckToolbar`(좌), `DeckViewer`(큰카드+스트립), `DeckFactBadge`+`DeckFactDetail`, `DeckExportModal`(v3). |

## 6. 토큰 매핑 (바이올렛 → forest-green, **실제 토큰명**)

| dc.html | shipped 토큰 |
|---|---|
| primary/그라디언트 | `var(--accent)`→`var(--accent-bright)` |
| 라벤더 틴트 | `var(--accent-subtle)` / `var(--bg-subtle)` |
| 사이드바(보라·**다크**) | `var(--surface)` — **라이트만**(제약 2, `--dark-bg` 사용 금지) |
| green(검증) | `var(--accent)` |
| amber(확인필요) | `var(--risk-medium-*)` |
| 텍스트/보더/그림자 | `var(--text-1)`·`var(--text-2)`·`var(--text-3)`, `var(--border)`, `var(--shadow-*)` |

(별칭 `--ink-1`은 존재하지 않음 → 원본 `--text-1` 사용. `--ink-2/3`은 별칭 존재.) 카드 내부 색은 `--set-*`/저작HTML — 불변.

## 7. 카피

- "충실성 검증·해자" → **"팩트 체크"** (+ "원문에 없는 수치는 따로 표시해요").
- 항목 배지: `원문에서 찾음` / `원문에 없음`. (출처 위치·"정확히 일치" 표기 금지 — §4.5.)
- "자연어로 고치기" → **"AI 도우미"** + "✦ AI에게 맡기기". (대안 "말로 고치기" — §9 미결정.)

## 8. 데이터 흐름 · 자동저장

- 폴링(`getStatus`→DONE/ERROR)→`getDeck`. 유지.
- **직접 편집 저장**: 자동저장(5초 idle)은 **html 저장 + 재검증만**(값싼 경로). **PNG 재렌더는 지연/명시적 트리거 or 백그라운드** — 5초마다 전 카드 Playwright 재렌더(120초)는 금지. `patchDeck`에 `render=false` 옵션(백엔드) 검토. **저장 시 선택 유지**(현 `setSelected(null)` 제거) — AI 도우미 "제안 대기"(=idle)가 자동저장에 파괴되지 않도록.
- **AI 편집**: §4.2 propose(미저장)→commit(`patchDeck`, 렌더). 되돌리기=스냅샷 `patchDeck`.
- 카드 이미지(`getDeckCardUrl`) 유지, 미완 fallback(§4.4).

## 9. 미결정 (구현 전 확정 vs 구현 중 OK)

**구현 전 확정 (② AI 계약 서브스펙 착수 전 — 재리뷰 major 반영):**
- **propose 입력 = 라이브 `serialize()` html**(DB html 아님) — eid 도달 + 미저장편집 보존.
- **eid = 불투명 난수 1회 스탬프**(위치·서수 폐기, MOVE/DELETE/INSERT 충돌 방지).
- **before/after = 프론트 DOM 텍스트 비교**(백엔드 파서 없음) + EDIT_SYSTEM `data-eid` 보존 규칙.
- propose 엔드포인트 형태(신규 route vs `persist=false`) → `docs/contracts/07` 갱신 선행.
- 자동저장 render 분리 시 **뷰 카드 stale 처리**(html만 저장 시 PNG는 뷰 진입/명시 트리거로 갱신).

**구현 중 OK:**
- 제안 세트 요소별 미세 조정(1차 세트는 §4.2에 명시).
- 팩트 상세 진입(배지 클릭 드로어 vs 편집 탭).
- 카피 최종("AI 도우미" vs "말로 고치기").

## 10. 테스트

- 실제 인프라 확인: `web` vitest(`vitest.config.mts`) 스위트 존재 여부·범위 우선 점검(rev1 가정 검증).
- 컴포넌트: 탭 전환, 요소 선택→target 페이로드, propose→before/after→commit/취소, 팩트 배지 초록/주황·재검증불가, 뷰 "이 카드 편집" index, Export 경고(+하드블록 부재).
- 회귀: 직접조작 계약(`SelectedInfo`·align·revertFlow), serialize 산출물 원본 호환.
- 시각 검증(완료 기준): forest-green 일치, 카드 색 불변, 뷰↔편집 크롬 통일.
- 백엔드: propose 미저장 보장, target 앵커 정확도.
- 접근성·키보드·반응형·빈/1장 덱 — 최소 케이스 명시.

## 11. 분해 (서브프로젝트 · 순서)

단일 계획으로 과대 → 4개로. **② 선행**(최대 리스크·나머지 의존).

- **① 앱 크롬 + 뷰** (순수 프론트): 상단바·좌 도구(축소)·탭 셸·`DeckViewer`(큰카드+스트립+바로편집)·팩트 배지·Export modal. 백엔드 무변.
- **② AI 도우미 계약** (백엔드+iframe, **최대 리스크·선행**): editorAgent `data-eid`+SELECTED 확장, `nlpatch` propose+target(docs/07), 스냅샷 되돌리기, before/after. → §4.2 전체.
- **③ 직접 편집 인스펙터** (1차 필드): `DeckInspector`. ②의 SELECTED 확장에 일부 의존.
- **④ 자동저장 분리 + 팩트 상세**: render 분리, 팩트 드로어.

각 서브프로젝트는 별도 스펙→플랜→구현 사이클. 이 문서는 상위 설계이며, 실제 착수는 ②(또는 ①) 서브스펙부터.

---

**한 줄 요약(rev2)**: AI 편집을 주로 하되 그 **계약(propose/commit·요소 target·스냅샷 되돌리기·editorAgent 확장)을 스코프 안에 명세**하고, 실현 불가한 도형/펜 도구·출처 카피는 축소·강등하며, 진짜 불변 자산(저작HTML·직렬화·deck_renderer)을 바로잡고, **② AI 계약을 선행하는 4개 서브프로젝트로 분해**한다.
