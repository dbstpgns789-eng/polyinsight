# Technical Audit Report — 카드 에디터 (`/editor/[jobId]`)

> **대상**: `src/pages/editor/[jobId].astro`
> **날짜**: 2026-05-19
> **방법론**: 5개 차원 기술 품질 검사 (Accessibility · Performance · Theming · Responsive · Anti-Patterns)

---

## Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | 3 | `.help-icon` focus outline 제거, `.done-card-btn` accessible label 없음 |
| 2 | Performance | 3 | rAF debounce·GPU transform 구현, listener 재등록 패턴 + will-change 미적용 |
| 3 | Theming | 3 | 토큰 시스템 탄탄, 하드코딩 oklch 5건 잔존 |
| 4 | Responsive Design | 2 | 900px 이하 차단, 900–1200px 구간 패널 과밀 |
| 5 | Anti-Patterns | 4 | AI 슬롭 징후 없음, 레이아웃 스래시 0건 |
| **Total** | | **15/20** | **Good — 약한 영역 개선 권장** |

---

## Anti-Patterns Verdict

**Pass.** AI 생성 UI 징후 없음.

- oklch hue 152 브랜드 팔레트 전체 일관 적용
- 그라디언트 텍스트·글래스모피즘·히어로 메트릭 없음
- `transform` + `opacity` 기반 애니메이션 — `layout-transition` 0건 (스캐너 확인)
- Pretendard Variable 국문 특화 폰트

---

## Executive Summary

- **Audit Health Score**: 15/20 (Good)
- **이슈 수**: P0×0 / P1×3 / P2×5 / P3×3 = 총 11건
- **Top 3 긴급 이슈**:
  1. `.help-icon` 키보드 포커스 아웃라인 제거 — WCAG 2.4.7 위반
  2. `.done-card-btn` "01"/"02" 텍스트만으로 스크린 리더 의미 전달 불가
  3. `role="listbox"` 썸네일 스트립에 Arrow키 핸들러 없어 ARIA 패턴 불완전
- **권장 다음 단계**: harden(a11y) → adapt(responsive) → polish

---

## Detailed Findings by Severity

### P1 — Major (출시 전 수정)

---

#### [P1-1] `.help-icon` 포커스 아웃라인 제거 — WCAG 2.4.7 위반

- **Location**: `<style>` 블록, `.help-icon:hover, .help-icon:focus-visible { opacity: 1; outline: none; }`
- **Category**: Accessibility
- **Impact**: 키보드 사용자가 Tab 키로 `?` 헬프 아이콘에 포커스를 이동해도 어디에 포커스가 있는지 시각적으로 알 수 없다. WCAG 2.4.7 (Focus Visible) Level AA 위반.
- **WCAG**: WCAG 2.1 SC 2.4.7
- **Recommendation**:
  ```css
  /* Before */
  .help-icon:hover, .help-icon:focus-visible { opacity: 1; outline: none; }

  /* After */
  .help-icon:hover { opacity: 1; }
  .help-icon:focus-visible { opacity: 1; outline: 2.5px solid var(--accent); outline-offset: 2px; }
  ```
- **Suggested command**: `/impeccable harden`

---

#### [P1-2] `.done-card-btn` accessible name 부재

- **Location**: `renderExport()` done case, `<button class="done-card-btn">${pad(i+1)}</button>`
- **Category**: Accessibility
- **Impact**: 스크린 리더가 "영일", "영이"로 읽어 사용자는 어떤 카드를 다운로드하는지 알 수 없다. `aria-label` 추가 필요.
- **WCAG**: WCAG 2.1 SC 4.1.2 (Name, Role, Value)
- **Recommendation**:
  ```js
  `<button class="done-card-btn" aria-label="카드 ${i+1} PNG 다운로드">${pad(i+1)}</button>`
  ```
- **Suggested command**: `/impeccable harden`

---

#### [P1-3] `role="listbox"` 썸네일 스트립에 Arrow키 핸들러 없음

- **Location**: `#thumb-strip`, HTML `role="listbox"`, JS `renderThumbnails()`
- **Category**: Accessibility
- **Impact**: `role="listbox"`는 Arrow키 탐색이 필수인 ARIA 패턴. 현재는 Tab으로만 접근 가능. 스크린 리더가 listbox 선언을 보고 Arrow키를 기대하지만 동작하지 않아 방향을 잃는다.
- **WCAG**: WCAG 2.1 SC 1.3.1, ARIA Authoring Practices Guide — Listbox Pattern
- **Recommendation**: `role="listbox"` → `role="group"` + `aria-label="카드 썸네일"` 로 교체 (Arrow키 구현 없이 간단히 수정). 또는 `#card-tabs`와 동일한 Arrow키 핸들러 구현.
- **Suggested command**: `/impeccable harden`

---

### P2 — Minor (다음 패스에서 수정)

---

#### [P2-1] `<input type="file">` label 없음

- **Location**: HTML `<input type="file" id="img-input" accept="image/*" hidden>`
- **Category**: Accessibility
- **Impact**: 숨겨진 input이지만 ARIA에서 label 없는 form 컨트롤로 노출될 수 있다. `aria-label` 추가로 안전하게 처리.
- **WCAG**: WCAG 2.1 SC 1.3.1
- **Recommendation**: `<input type="file" id="img-input" accept="image/*" hidden aria-label="이미지 파일 선택">`
- **Suggested command**: `/impeccable harden`

---

#### [P2-2] `.export-card`에 `will-change: transform` 없음

- **Location**: `.export-card` CSS
- **Category**: Performance
- **Impact**: `.export-card`는 `transform: translateY()` 트랜지션을 사용하지만 `will-change` 힌트가 없어 브라우저가 사전 합성 레이어를 준비하지 못한다. 오버레이 진입 시 첫 프레임 jank 가능.
- **Recommendation**:
  ```css
  .export-card { will-change: transform; }
  /* overlay 닫힌 상태에서는 해제 */
  .export-overlay:not(.is-open) .export-card { will-change: auto; }
  ```
- **Suggested command**: `/impeccable animate`

---

#### [P2-3] 하드코딩 oklch 값 5건 — 토큰 미등록

- **Location**: 
  - `:642` `.img-delete-btn { background: oklch(8% 0.01 152 / 0.55); }`
  - `:454` `.risk-banner--critical { border: 1px solid oklch(86% 0.07 25); }`
  - `:459` `.risk-banner--high { border: 1px solid oklch(86% 0.08 52); }`
  - toast CSS: `oklch(100% 0 0 / 0.35)`, `oklch(100% 0 0 / 0.55)`, `oklch(100% 0 0 / 0.12)`
- **Category**: Theming
- **Impact**: 토큰 없이 하드코딩된 값은 테마 변경 시 누락되거나 색조 일관성이 깨진다.
- **Recommendation**: `Layout.astro :root`에 토큰 추가:
  ```css
  --overlay-scrim:        oklch(8% 0.01 152 / 0.55);
  --risk-critical-line:   oklch(86% 0.07 25);
  --risk-high-line:       oklch(86% 0.08 52);
  --on-dark-faint:        oklch(100% 0 0 / 0.35);
  --on-dark-mid:          oklch(100% 0 0 / 0.55);
  --on-dark-hover:        oklch(100% 0 0 / 0.12);
  ```
- **Suggested command**: `/impeccable polish`

---

#### [P2-4] 900–1200px 뷰포트에서 패널 과밀

- **Location**: `.editor-body { grid-template-columns: 300px 1fr 260px; }`
- **Category**: Responsive Design
- **Impact**: 900px 초과 즉시 에디터가 표시되지만 `300 + 260 = 560px` 고정 사이드바 + 1fr 가변 중앙. 1000px 뷰포트에서 중앙 미리보기 영역은 440px에 불과해 카드 미리보기가 매우 작아진다. 13인치 노트북(1280px, 90% 줌 시 ~1150px) 사용자에게 불편.
- **Recommendation**:
  ```css
  @media (max-width: 1200px) {
    .editor-body { grid-template-columns: 260px 1fr 220px; }
  }
  ```
- **Suggested command**: `/impeccable adapt`

---

#### [P2-5] `.preflight-check` 체크마크 — SR 텍스트 없음

- **Location**: CSS `.preflight-check::after { content:''; ... transform: rotate(-45deg); }`, JS `renderExport()` PREFLIGHT case
- **Category**: Accessibility
- **Impact**: 체크 여부가 CSS 아이콘으로만 전달된다. 텍스트 내용이 함께 있어 의미 전달은 가능하지만, 아이콘에 role/label이 없어 `aria-hidden="true"` 이미 적용됨 ✅ — 텍스트로 의미가 전달되므로 실제 이슈는 낮음.
- **Recommendation**: 현재 `aria-hidden="true"` 적용됨. 실제로는 OK. 하지만 `.preflight-warn`도 `aria-hidden="true"` 동일 처리 확인 필요.
- **Suggested command**: `/impeccable harden`

---

### P3 — Polish

---

#### [P3-1] 이벤트 리스너 재등록 패턴 — `renderCardTabs()` / `renderThumbnails()`

- **Location**: `renderCardTabs()`, `renderThumbnails()` — 매 렌더 시 innerHTML 교체 후 `querySelectorAll().forEach(addEventListener)`
- **Category**: Performance
- **Impact**: 카드 수×렌더 횟수만큼 이벤트 리스너 생성. GC가 처리하므로 실제 메모리 누수 없음. 단, 20장 이상 대형 세트에서 미세 지연 가능.
- **Recommendation**: 이벤트 위임(event delegation)으로 교체.
  ```js
  // 부모에 한 번만 등록
  document.getElementById('card-tabs').addEventListener('click', e => {
    const btn = e.target.closest('[role="tab"]');
    if (btn) selectCard(+btn.dataset.idx);
  });
  ```
- **Suggested command**: `/impeccable optimize`

---

#### [P3-2] 썸네일 스트립 스크롤 어포던스 없음

- **Location**: `.thumb-strip { scrollbar-width: none; }`, CSS
- **Category**: Accessibility / UX
- **Impact**: 카드가 가로로 넘칠 때 스크롤 가능 여부를 알 수 없다.
- **Recommendation**: 썸네일 컨테이너 양 끝에 fade gradient mask 추가.
  ```css
  .thumb-strip { mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); }
  ```
- **Suggested command**: `/impeccable polish`

---

#### [P3-3] `backdrop-filter: blur(6px)` — reduced-motion 미처리

- **Location**: `.export-overlay { backdrop-filter: blur(6px); }`
- **Category**: Performance / Accessibility
- **Impact**: `prefers-reduced-motion` 미디어 쿼리에서 blur가 그대로 유지된다. Blur는 애니메이션이 아니므로 엄밀한 위반은 아니나, 저사양 기기에서 GPU 부하 기여.
- **Recommendation**: reduced-motion에서 blur 제거는 선택적. 현재 reduced-motion 블록에 포함해도 무방.
- **Suggested command**: `/impeccable animate`

---

## Patterns & Systemic Issues

1. **ARIA role 선언은 있으나 대응 키보드 패턴 미구현**: `role="listbox"` (thumb-strip), `role="tablist"` + ArrowKey 구현됨 (card-tabs). 일관성 있게 모든 복합 위젯에 키보드 패턴을 완성해야 한다.

2. **하드코딩 oklch 값이 CSS와 JS 모두에 산재**: 토큰 시스템 잘 갖춰져 있으나 엣지 케이스(오버레이 스크림, 토스트 화이트) 값들이 토큰 없이 사용됨. 토큰 등록 정책을 일관되게 적용 필요.

---

## Positive Findings

- **rAF 디바운스** textarea input 처리 — 필드 편집 중 preview 재렌더를 매 keystroke마다 트리거하지 않음 ✅
- **Object URL 생명주기 관리** — `createObjectURL` / `revokeObjectURL` 짝을 맞춰 메모리 누수 방지 ✅
- **Focus trap + aria-hidden 교체** 내보내기 모달 — WCAG 모달 다이얼로그 패턴 정확히 구현 ✅
- **`aria-live` 저장 상태** — 스크린 리더 사용자에게 저장 상태 실시간 고지 ✅
- **GPU transform 기반 애니메이션** — render-fill, export-card 모두 `transform` 사용, layout thrash 0건 ✅
- **oklch 브랜드 토큰 시스템** — 모든 색상이 oklch 팔레트로 일관 관리됨 ✅

---

## Recommended Actions (Priority Order)

| 순서 | 우선순위 | 커맨드 | 범위 |
|-----|---------|--------|------|
| 1 | P1 | `/impeccable harden` | help-icon focus outline · done-card-btn aria-label · listbox→group · img-input label |
| 2 | P2 | `/impeccable adapt` | 900–1200px 미디어 쿼리 패널 레이아웃 |
| 3 | P2 | `/impeccable animate` | export-card will-change · backdrop-filter reduced-motion |
| 4 | P2 | `/impeccable polish` | 하드코딩 oklch 토큰화 · 썸네일 스크롤 어포던스 |
| 5 | P3 | `/impeccable optimize` | 이벤트 위임 패턴 적용 |
| 6 | — | `/impeccable polish` | 전체 마무리 패스 |

> 한 번에 실행하거나 하나씩 진행하거나 원하는 순서로 요청해 주세요.
> 수정 완료 후 `/impeccable audit`를 재실행하면 점수 변화를 트래킹할 수 있습니다.
