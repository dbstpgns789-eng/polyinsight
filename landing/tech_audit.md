# PolyInsight — Technical Audit Report

> 대상: 전체 프로젝트 (`src/layouts/Layout.astro`, `src/pages/index.astro`, `src/components/UploadModal.astro`, `src/pages/editor/[jobId].astro`)
> 기준: Accessibility (WCAG 2.1 AA) · Performance · Theming · Responsive · Anti-Patterns
> 작성일: 2026-05-19

---

## Audit Health Score

| # | 차원 | 점수 | 핵심 발견 |
|---|------|------|-----------|
| 1 | Accessibility | 2 / 4 | Tab ARIA 패턴 미완성, 모달 포커스 트랩 누락 |
| 2 | Performance | 3 / 4 | Object URL 메모리 누수, 키입력마다 innerHTML 재렌더 |
| 3 | Theming | 2 / 4 | `--accent` 값 15회+ 하드코딩, 위험도 색상 토큰 없음 |
| 4 | Responsive Design | 3 / 4 | 데스크탑 전용 의도적 설계, 중간 뷰포트 압착 |
| 5 | Anti-Patterns | 4 / 4 | AI slop 없음, 브랜드 정체성 일관성 우수 |
| **합계** | | **14 / 20** | **Good — 접근성·테마 차원 집중 보강 필요** |

---

## Anti-Patterns 판정 (최우선 검토)

**판정: PASS — AI-generated 외관 없음.**

- 녹색 계열 브랜드 액센트 (SaaS 관용 블루/퍼플 아님) ✓
- 그라디언트 텍스트 없음 ✓
- 글래스모피즘 없음 (오버레이 blur는 기능적 사용, 장식 아님) ✓
- 영웅 지표 카드 그리드 없음 ✓
- 범용 시스템 폰트 대신 Pretendard 명시 ✓
- 구체적이고 제품 목적에 집중된 카피 ✓

---

## Executive Summary

- **Audit Health Score: 14/20 (Good)**
- 발견 이슈: P1 × 5건, P2 × 7건, P3 × 5건
- **즉시 수정 필요 (P1)**: 접근성 WCAG AA 위반 3건 + 메모리 누수 1건 + ARIA 역할 오용 1건
- **다음 패스 (P2)**: 토큰 체계 정비, 키보드 UX, 렌더 최적화

---

## 세부 발견 — 심각도 순

---

### ─ Accessibility ─────────────────────────────────────

#### [P1] Tab ARIA 패턴 미완성
- **위치**: `editor/[jobId].astro` — `#card-tabs`, `renderCardTabs()`
- **카테고리**: Accessibility
- **WCAG**: 4.1.2 Name, Role, Value (Level A)
- **영향**: 스크린리더 사용자가 카드 탭을 탐색할 수 없음. `role="tablist"` + `role="tab"`을 사용하지만 대응하는 `role="tabpanel"` 없음. 또한 WAI-ARIA Authoring Practices가 요구하는 `ArrowLeft`/`ArrowRight` 키보드 탐색 미구현.
- **현재 코드**:
  ```js
  // renderCardTabs(): role="tab"은 있으나 tabpanel, aria-controls 없음
  `<button class="card-tab" role="tab" aria-selected="${...}">`
  ```
- **권장 수정**:
  ```js
  // 탭에 aria-controls 추가
  `<button role="tab" aria-controls="panel-${i}" aria-selected="${...}">`
  // 패널 래퍼에 tabpanel 추가
  `<div role="tabpanel" id="panel-${i}" aria-labelledby="tab-${i}">`
  // keydown 이벤트: ArrowLeft/Right로 인접 탭 포커스
  ```

---

#### [P1] Export 모달 포커스 트랩 미구현
- **위치**: `editor/[jobId].astro` — `openExport()`, export overlay
- **카테고리**: Accessibility
- **WCAG**: 2.1.1 Keyboard (Level A)
- **영향**: 내보내기 모달이 열려 있을 때 Tab 키로 배경 에디터 요소(저장 버튼, 카드 탭, 텍스트에리어)에 접근 가능. 모달 외부 요소를 활성화할 경우 상태 오염 위험.
- **비교**: `UploadModal.astro`는 포커스 트랩이 올바르게 구현됨 — 동일 패턴 적용 필요.
- **권장 수정**:
  ```js
  // openExport() 내부에 포커스 트랩 로직 추가
  // (UploadModal의 focusTrap 함수 참조)
  ```

---

#### [P1] `role="contentinfo"` 랜드마크 오용
- **위치**: `editor/[jobId].astro` L107 — `<footer class="actionbar" role="contentinfo">`
- **카테고리**: Accessibility
- **WCAG**: 1.3.6 Identify Purpose (Level AAA), ARIA Landmark 사용 기준
- **영향**: `contentinfo`는 페이지 수준의 저작권·법적고지 등을 담는 랜드마크. ActionBar(내보내기 액션 영역)에 사용하면 스크린리더의 랜드마크 탐색이 오도됨. 올바른 역할은 `toolbar` 또는 없음.
- **권장 수정**:
  ```html
  <!-- role="contentinfo" → role="toolbar" 또는 제거 -->
  <footer class="actionbar" role="toolbar" aria-label="내보내기 액션">
  ```

---

#### [P2] Thumbnail 컨테이너 키보드 탐색 미구현
- **위치**: `editor/[jobId].astro` — `#thumb-strip`, `renderThumbnails()`
- **카테고리**: Accessibility
- **WCAG**: 2.1.1 Keyboard (Level A)
- **영향**: `role="listbox"` + `role="option"` 패턴은 Up/Down 화살표 키 탐색을 요구하지만 미구현. 마우스 없이 썸네일 탐색 불가.
- **권장 수정**: `role="listbox"` 제거 후 일반 버튼 목록으로 유지하거나, `ArrowLeft`/`ArrowRight` keydown 핸들러 추가.

---

#### [P2] 모달 열릴 때 배경 `aria-hidden` 미처리
- **위치**: `editor/[jobId].astro` — `openExport()` / `UploadModal.astro` — `openModal()`
- **카테고리**: Accessibility
- **WCAG**: 4.1.3 Status Messages (Level AA)
- **영향**: 모달이 열려 있을 때 배경 콘텐츠가 `aria-hidden="true"` 처리되지 않아 스크린리더가 두 컨텍스트 모두 읽을 수 있음.
- **권장 수정**:
  ```js
  // openExport() 내
  document.getElementById('state-editor').setAttribute('aria-hidden', 'true');
  // closeExport() 내
  document.getElementById('state-editor').removeAttribute('aria-hidden');
  ```

---

### ─ Performance ─────────────────────────────────────

#### [P1] Object URL 메모리 누수
- **위치**: `editor/[jobId].astro` — `setupImageSlot()` L1250
- **카테고리**: Performance
- **영향**: `URL.createObjectURL(file)`로 생성된 blob URL이 `URL.revokeObjectURL()` 없이 이미지 삭제·교체 시 메모리에 남음. 카드 수 × 교체 횟수에 비례해 메모리 증가. 장시간 세션에서 누적될 경우 브라우저 메모리 압박.
- **현재 코드**:
  ```js
  const url = URL.createObjectURL(file);
  preview.src = url;
  card.imageUrl = url;
  // ← URL.revokeObjectURL 없음
  ```
- **권장 수정**:
  ```js
  // 교체 또는 삭제 시 기존 URL 해제
  if (card.imageUrl) URL.revokeObjectURL(card.imageUrl);
  const url = URL.createObjectURL(file);
  ```

---

#### [P2] 키입력마다 전체 카드 innerHTML 재렌더
- **위치**: `editor/[jobId].astro` — `renderContentPanel()` input 이벤트 → `renderPreviewCard()`
- **카테고리**: Performance
- **영향**: textarea 한 글자 입력마다 `buildCardHTML()`이 실행되고 `preview-card.innerHTML`이 전체 교체됨. HTML 재파싱 + DOM 전체 재생성. 실제 사용자 체감은 낮지만 저사양 기기에서 버벅임 가능.
- **권장 수정**: `requestAnimationFrame` 기반 debounce 적용.
  ```js
  let previewRaf = null;
  ta.addEventListener('input', () => {
    state.cards[state.cardIdx].fields[+ta.dataset.fi].value = ta.value;
    if (previewRaf) cancelAnimationFrame(previewRaf);
    previewRaf = requestAnimationFrame(renderPreviewCard);
    scheduleAutoSave();
  });
  ```

---

#### [P2] innerHTML 렌더 시 이벤트 리스너 매번 재등록
- **위치**: `editor/[jobId].astro` — `renderCardTabs()`, `renderThumbnails()`, `renderContentPanel()`
- **카테고리**: Performance
- **영향**: 카드 탭·썸네일 클릭 이벤트 리스너가 렌더마다 새로 등록됨. 기존 리스너는 DOM에서 제거되므로 실제 누수는 없지만 이벤트 위임(event delegation) 패턴이 더 효율적.
- **권장 수정**: 컨테이너에 한 번만 이벤트 리스너 등록 후 `event.target.closest('[data-idx]')`로 위임.

---

#### [P3] Pretendard CDN 폰트 스토리지 차단
- **위치**: `Layout.astro` L24
- **카테고리**: Performance
- **영향**: Edge 브라우저 추적 방지(Tracking Prevention)가 jsDelivr CDN의 스토리지 접근을 차단. 폰트 캐시 불가 → 페이지 방문마다 폰트 재다운로드. 한국 사용자 중 Edge 점유율에서 반복 발생.
- **권장 수정**:
  ```html
  <!-- 옵션 A: DNS-prefetch 추가 (현재 preconnect만 있음) -->
  <link rel="dns-prefetch" href="https://cdn.jsdelivr.net">
  
  <!-- 옵션 B (장기): npm install pretendard 후 로컬 서빙 -->
  ```

---

### ─ Theming ─────────────────────────────────────────

#### [P2] `var(--accent)` 값 직접 하드코딩 — 15회+
- **위치**: `editor/[jobId].astro` — `<style is:global>` cv-* 블록
- **카테고리**: Theming
- **영향**: `--accent`의 실제 값인 `oklch(38% 0.14 152)`가 `cv-header`, `cv-divider`, `cv-stat`, `cv-citation`, `cv-point::before` 등 15곳 이상에서 직접 사용됨. 브랜드 색상 변경 시 모든 위치를 수동 수정해야 함.
- **발생 위치 샘플**:
  ```css
  .cv-header  { background: oklch(38% 0.14 152); } /* var(--accent) 써야 함 */
  .cv-divider { background: oklch(38% 0.14 152); }
  .cv-stat    { color:      oklch(38% 0.14 152); }
  .cv-citation { color:     oklch(38% 0.14 152); }
  ```
- **권장 수정**: 모든 인스턴스를 `var(--accent)` / `var(--accent-faint)` 등으로 교체.

---

#### [P2] 위험도 색상 토큰 미정의
- **위치**: `editor/[jobId].astro` — `.field--critical`, `.field--high`, `.risk-banner--*`, `.risk-tag--*`, `.btn-confirm`
- **카테고리**: Theming
- **영향**: CRITICAL/HIGH/MEDIUM 위험도 색상이 6개 이상 규칙에 개별 하드코딩됨. 위험도 색상 체계를 변경하려면 분산된 모든 위치를 찾아 수정해야 함.
- **현재 산재 위치**:
  ```css
  .field--critical { border-color: oklch(78% 0.1 25); }
  .risk-banner--critical { background: oklch(97% 0.025 25); }
  .risk-tag--critical { background: oklch(94% 0.04 25); }
  .btn-confirm { background: oklch(40% 0.16 25); }
  /* ... 추가 4곳 */
  ```
- **권장 수정**: `:root`에 토큰 추가:
  ```css
  --risk-critical:        oklch(40% 0.16 25);
  --risk-critical-subtle: oklch(97% 0.025 25);
  --risk-critical-border: oklch(78% 0.1 25);
  --risk-high:            oklch(42% 0.18 50);
  --risk-high-subtle:     oklch(97% 0.03 50);
  ```

---

#### [P3] 다크 모드 미지원
- **위치**: 전체 프로젝트
- **카테고리**: Theming
- **영향**: `@media (prefers-color-scheme: dark)` 없음. 현재 라이트 온리. 다크 모드 선호 사용자 경험 저하. 현재는 B2B 데모 단계라 critical하지 않으나 프로덕션 전 대응 필요.

---

#### [P3] Layout.astro `.section--dark` 하드코딩 색상
- **위치**: `Layout.astro` L207
- **카테고리**: Theming
- **현재**: `.section--dark { color: oklch(92% 0.008 152); }` — `--dark-bg`·`--dark-bg-2` 토큰이 있으나 텍스트 색상은 토큰 없이 하드코딩.

---

### ─ Responsive Design ─────────────────────────────────

#### [P2] 중간 뷰포트(769–900px) 3패널 압착
- **위치**: `editor/[jobId].astro` — `.editor-body`
- **카테고리**: Responsive Design
- **영향**: `grid-template-columns: 300px 1fr 260px`에서 모바일 차단은 `≤768px`. 769px 뷰포트에서는 중앙 패널이 `769 - 300 - 260 - 경계선 2px ≈ 207px`로 압착됨. 카드 미리보기(`min(400px, 100%)`)가 207px로 축소되어 가독성 저하.
- **권장 수정**: 모바일 차단 브레이크포인트를 `≤900px`로 확장하거나, 중간 뷰포트에서 2패널(콘텐츠 + 프리뷰)로 전환.

---

#### [P3] 카드 탭 터치 타깃 28px
- **위치**: `editor/[jobId].astro` — `.card-tab { height: 28px }`
- **카테고리**: Responsive Design
- **영향**: WCAG 2.5.5 Target Size 권장 기준 44px 미달. 데스크탑 전용이라 실제 문제는 없으나, 미래 태블릿 지원 시 수정 필요.

---

## 패턴 분석 — 시스템적 이슈

### 색상 토큰 비일관성 (테마 차원 전체)
`Layout.astro`의 `:root`에 `--accent`, `--bg`, `--surface` 등 잘 정의되어 있으나, **에디터 페이지 내 동적 콘텐츠(`cv-*`)와 위험도 관련 색상은 토큰 없이 리터럴 값을 반복 사용**. 토큰 시스템의 절반만 활용됨. 리팩토링 기준: `oklch()` 리터럴이 2회 이상 반복되면 토큰화.

### 접근성 패턴 단절 (에디터 페이지)
`UploadModal.astro`는 포커스 트랩, `aria-modal`, `aria-hidden`, 키보드 ESC를 모두 구현. 에디터의 Export 모달은 같은 패턴이 필요하지만 미적용. 모달 관련 접근성 로직을 **공유 헬퍼**로 추출하면 두 곳 모두 개선됨.

---

## 잘 된 점

| 항목 | 평가 |
|------|------|
| 디자인 토큰 기반 구조 | `--accent`, `--bg`, `--surface`, spacing, typography 체계적 정의 |
| `UploadModal` 접근성 | `aria-modal`, `aria-live`, `role="progressbar"`, `aria-valuenow` 정확히 구현 |
| `prefers-reduced-motion` | 에디터 export modal에 `@media (prefers-reduced-motion: reduce)` 적용 |
| `scroll-behavior: smooth` | HTML 수준에서 부드러운 스크롤 제어 |
| 폰트 폴백 체인 | Pretendard → Apple SD Gothic Neo → system-ui 안전한 다단 폴백 |
| RequestAnimationFrame 사용 | export progress bar, pipeline progress에 RAF 정확히 활용 |
| 드래그 카운터 패턴 | dragenter/dragleave 카운터로 자식 요소 진입 시 flicker 방지 — 올바른 구현 |
| oklch 색상 체계 | P3 색상 공간 기반으로 일관된 색조 관계 유지 |
| `word-break: keep-all` | 한국어 줄바꿈 품질 전역 적용 |

---

## 권장 후속 작업 (우선순위 순)

| 순서 | 심각도 | 작업 | 설명 |
|------|--------|------|------|
| 1 | P1 | Object URL 메모리 누수 수정 | `URL.revokeObjectURL()` 추가 — 15분 |
| 2 | P1 | Export 모달 포커스 트랩 | UploadModal 패턴 복사 적용 — 30분 |
| 3 | P1 | `role="contentinfo"` → `role="toolbar"` | 1줄 수정 |
| 4 | P1 | Tab ARIA 패턴 완성 | `tabpanel`, `aria-controls`, 화살표 키 — 1시간 |
| 5 | P2 | cv-* `var(--accent)` 토큰 교체 | 전체 replace — 20분 |
| 6 | P2 | 위험도 색상 토큰 추가 | `:root` 5개 토큰 + 참조 교체 — 30분 |
| 7 | P2 | Preview debounce (rAF) | 키입력 렌더 최적화 — 10분 |
| 8 | P2 | 배경 `aria-hidden` 모달 개폐 시 처리 | 2줄 추가 — 5분 |
| 9 | P2 | 중간 뷰포트(769–900px) 레이아웃 | 모바일 차단 범위 확장 — 15분 |
| 10 | P3 | DNS-prefetch 추가 | 폰트 CDN 캐시 개선 — 1줄 |

> 수정 후 `impeccable audit`을 재실행하면 점수 개선 추적이 가능합니다.

---

*정적 코드 분석 기반 리포트. 실제 브라우저 성능 프로파일링 및 스크린리더 수동 테스트 별도 권장.*
