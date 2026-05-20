# Auth Pages Technical Audit Report

> Target: `/login` · `/signup` (AuthLayout + AuthForm)
> Files: `web/src/components/auth/AuthLayout.tsx`, `web/src/components/auth/AuthForm.tsx`, `web/src/app/globals.css` (auth section)
> Date: 2026-05-20
> Standard: WCAG 2.1 AA

---

## Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | 2 | WCAG AA 대비 실패 4건 (P1) — `var(--text-3)` 계열 전반 |
| 2 | Performance | 3 | `box-shadow` transition repaint, `prefers-reduced-motion` 미적용 |
| 3 | Theming | 3 | 인라인 OKLCH 리터럴 10+개, `.btn-primary` `color: #fff` (시스템 이슈) |
| 4 | Responsive | 3 | `--gutter` 정의 확인, btn-lg/input 터치 타겟 통과, minor 개선 여지 |
| 5 | Anti-Patterns | 3 | hero-metric 수정됨, split-screen 패턴 잔존하지만 차별화 요소 존재 |
| **Total** | | **14/20** | **Good — 접근성 차원 집중 개선 필요** |

---

## Anti-Patterns Verdict

**Pass (with conditions).** 자동 스캐너 클린(0 findings). 이전 세션에서 hero-metric 밴 패턴이 수정되어 큰 위반은 없음. 잔존 위험: split-screen dark-left/light-right 레이아웃 자체는 가장 흔한 AI 생성 auth 패턴과 동일하나, cite chip(`Table 2, p.8`)이 차별화 앵커로 기능. 현재 수준은 "AI가 만든 것 같다"는 즉각적 반응을 유발하지 않음.

---

## Executive Summary

- **Audit Health Score: 14/20** (Good)
- **총 이슈: P0 0건 / P1 4건 / P2 6건 / P3 4건**
- **최우선 해결 항목:** WCAG AA 대비 실패 4건 — 모두 접근성 법적 기준 미달
- **추천 대응:** P1 → P2 → P3 순서, 각 대응 후 재감사

---

## Detailed Findings by Severity

### P1 — WCAG AA 대비 실패 (4건)

---

**[P1-A] `var(--text-3)` on `var(--surface)` — 4개 요소 일괄 실패**

- **Location:** `globals.css` — `.auth-form__sub`, `.auth-terms`, `.auth-switch`, `.auth-divider`
- **Category:** Accessibility
- **Contrast ratio:** `oklch(63% 0.008 152)` on `oklch(99.8% 0.002 152)` ≈ **2.5:1**
- **Required:** 4.5:1 (WCAG AA, small text)
- **WCAG:** SC 1.4.3 Contrast (Minimum)
- **Impact:** 저시력 사용자, 밝은 환경 사용자, 고령 사용자 모두 텍스트를 읽기 어려움. 회원가입 약관, 로그인 전환 링크, "또는" 구분선 모두 포함됨.
- **Recommendation:** `var(--text-3)` 대신 `var(--text-2)` (`oklch(44% 0.012 152)`, ~4.7:1) 사용. 또는 해당 요소들의 색상 토큰을 `--text-subtle`로 신규 정의하고 WCAG AA 통과값으로 설정.
- **Suggested command:** `/impeccable harden auth 접근성 대비 수정`

---

**[P1-B] `var(--accent)` on `var(--dark-bg)` — 로고 "Insight" 스팬**

- **Location:** `globals.css:838` — `.auth-brand__logo span { color: var(--accent); }`
- **Category:** Accessibility
- **Contrast ratio:** `oklch(38% 0.14 152)` on `oklch(14% 0.04 152)` ≈ **2.7:1**
- **Required:** 4.5:1 (WCAG AA, 1.125rem 700 weight는 large text 기준인 18.67px bold 미달)
- **WCAG:** SC 1.4.3
- **Impact:** 화면 확대 없이 로고에서 "Insight" 부분이 다크 배경에서 식별 어려움.
- **Recommendation:** 다크 패널에서의 accent 노출을 `oklch(62% 0.13 152)` 이상의 밝은 그린으로 교체. 또는 로고 스팬을 화이트 계열(`oklch(90% 0.01 152)`)로 처리하고 accent 사용 자제.
- **Suggested command:** `/impeccable harden auth 로고 대비 수정`

---

**[P1-C] `var(--accent)` on cite chip background — 인용 칩 텍스트**

- **Location:** `globals.css:910` — `.auth-proof-card__cite { color: var(--accent); background: oklch(20% 0.055 152); }`
- **Category:** Accessibility
- **Contrast ratio:** `oklch(38% 0.14 152)` on `oklch(20% 0.055 152)` ≈ **2.2:1**
- **Required:** 4.5:1 (11px small text는 AA에서도 4.5:1 필요)
- **WCAG:** SC 1.4.3
- **Impact:** cite chip이 제품의 핵심 신뢰 증거인데, 실제로 읽기 어려움. 기능적 목적의 텍스트가 장식 수준으로 저하됨.
- **Recommendation:** cite chip 텍스트를 `oklch(72% 0.015 152)` 이상으로 밝히거나, chip 배경을 더 밝게. 또는 chip 텍스트를 `oklch(90% 0.015 152)` (finding과 동일 계열)으로.
- **Suggested command:** `/impeccable harden auth 인용칩 대비 수정`

---

**[P1-D] `oklch(40% 0.04 152)` on `var(--dark-bg-2)` — 증거 카드 레이블**

- **Location:** `globals.css:887` — `.auth-proof-card__label { color: oklch(40% 0.04 152); }`
- **Background:** `var(--dark-bg-2)` = `oklch(19% 0.04 152)`
- **Category:** Accessibility
- **Contrast ratio:** ≈ **2.5:1**
- **Required:** 4.5:1
- **WCAG:** SC 1.4.3
- **Impact:** "연구 결과" / "4 / 5 — 예시" 레이블이 판독 불가 수준.
- **Recommendation:** 레이블 색상을 `oklch(55% 0.04 152)` 이상(~4.8:1)으로 높임.
- **Suggested command:** `/impeccable harden auth 증거카드 레이블 대비 수정`

---

### P2 — 주요 개선 항목 (6건)

---

**[P2-A] `outline: none` without `:focus-visible` pattern**

- **Location:** `globals.css:982` — `.auth-input { outline: none; }`
- **Category:** Accessibility
- **WCAG:** SC 2.4.7 Focus Visible (AA)
- **Impact:** `:focus` 상태에서 box-shadow로 대체하지만, 마우스 클릭에도 포커스 링이 표시됨 (노이즈). 더 중요하게는 일부 보조기술 환경에서 box-shadow 포커스 링이 시스템 포커스 표시기를 덮어씌울 수 있음. 업계 표준은 `:focus:not(:focus-visible)` 패턴으로 마우스 포커스와 키보드 포커스를 분리하는 것.
- **Recommendation:** `outline: none` 제거 → `:focus:not(:focus-visible) { box-shadow: none; border-color: var(--border); }` 추가. `:focus-visible`만 box-shadow 링 표시.
- **Suggested command:** `/impeccable harden auth 포커스 가시성`

---

**[P2-B] `prefers-reduced-motion` 미적용 — 스피너 애니메이션**

- **Location:** `globals.css:1058` — `.auth-spinner { animation: auth-spin 0.75s linear infinite; }`
- **Category:** Accessibility / Performance
- **WCAG:** SC 2.3.3 Animation from Interactions (AAA), 실용적 AA 기준
- **Impact:** 전정계 장애(vestibular disorder) 사용자에게 무한 회전 애니메이션은 신체 불쾌감을 유발. `prefers-reduced-motion: reduce` 미디어 쿼리로 guard해야 함.
- **Recommendation:**
  ```css
  @media (prefers-reduced-motion: reduce) {
    .auth-spinner { animation: none; opacity: 0.6; }
  }
  ```
- **Suggested command:** `/impeccable animate auth 모션 접근성`

---

**[P2-C] 모바일에서 페이지 `<h1>` 부재**

- **Location:** `AuthLayout.tsx:7` — `.auth-brand { aria-hidden="true" }` 내부의 `<h1>`이 숨겨짐. 모바일 `.auth-mobile-brand`에는 `<h1>` 없음.
- **Category:** Accessibility
- **WCAG:** SC 1.3.1 Info and Relationships (A)
- **Impact:** 모바일에서 스크린 리더 사용자가 페이지에서 메인 헤딩(h1)을 찾을 수 없음. `<h2>`("로그인"/"회원가입")가 첫 번째 헤딩이 되는 계층 오류.
- **Recommendation:** `.auth-mobile-brand` 내부 `<p>` 설명 텍스트를 `<h1>`으로 교체하거나, 폼 `<h2>`를 시각적으로 h2 스타일이지만 의미상 `<h1>`으로 변경 (모바일에서만). 또는 `.auth-panel__inner`에 숨김 `<h1 class="sr-only">PolyInsight 로그인</h1>` 추가.
- **Suggested command:** `/impeccable harden auth 헤딩 계층 구조`

---

**[P2-D] 인라인 OKLCH 리터럴 10+개 — 토큰화 미완료**

- **Location:** `globals.css:834,853,859,870,887,893,900,911,912,987,990` (auth 섹션)
- **Category:** Theming
- **Impact:** 브랜드 hue가 152에서 변경될 경우 auth 섹션만 수동 업데이트 필요. 다크 패널 전경 색상에 공식 토큰이 없어 일관성 유지 어려움. 다른 컴포넌트에서 동일 색상 재사용 시 중복 리터럴 증가.
- **Affected literals (명명 필요):**
  | 리터럴 | 용도 | 제안 토큰명 |
  |--------|------|------------|
  | `oklch(92% 0.008 152)` | 다크 패널 로고 텍스트 | `--dark-text-1` |
  | `oklch(95% 0.01 152)` | 다크 패널 헤드라인 | `--dark-text-1` (동일) |
  | `oklch(55% 0.04 152)` | 다크 패널 서브텍스트 | `--dark-text-2` |
  | `oklch(40% 0.04 152)` | 증거카드 레이블 | `--dark-text-3` |
  | `oklch(24% 0.045 152)` | 증거카드 보더 | `--dark-border` |
  | `oklch(20% 0.055 152)` | 인용칩 배경 | `--dark-chip-bg` |
  | `oklch(28% 0.07 152)` | 인용칩 보더 | `--dark-chip-border` |
  | `oklch(78% 0.012 152)` | input hover 보더 | `--border-hover` |
  | `oklch(38% 0.14 152 / 0.12)` | input 포커스 링 | `var(--accent)` + opacity modifier |
- **Suggested command:** `/impeccable extract auth 다크 패널 토큰`

---

**[P2-E] `.btn-primary { color: #fff }` — 시스템 레벨 hex 사용**

- **Location:** `globals.css:209` — `.btn-primary { color: #fff; }`
- **Category:** Theming
- **Impact:** DESIGN.md "Don't use pure `#000` or `#fff`" 위반. 버튼 텍스트 컬러가 hue 152 틴팅 없는 순수 흰색. Auth 페이지의 primary 버튼 모두 영향.
- **Recommendation:** `color: oklch(99% 0.003 152)` (거의 흰색이지만 틴팅됨)으로 교체.
- **Suggested command:** `/impeccable polish globals 버튼 색상 토큰 정리`

---

**[P2-F] 고아(orphaned) CSS 클래스 `.auth-field__forgot`**

- **Location:** `globals.css:971` — `.auth-field__forgot { text-align: right; margin-top: calc(-1 * var(--s1)); }`
- **Category:** Performance / Theming (dead code)
- **Impact:** 이 클래스를 사용하던 HTML 요소(`비밀번호를 잊으셨나요?` 링크)가 이전 critique 대응에서 제거됨. CSS가 남아 데드 코드로 존재. 향후 동일 클래스를 다른 목적으로 오용할 위험.
- **Recommendation:** `.auth-field__forgot` CSS 블록 삭제.
- **Suggested command:** `/impeccable polish auth CSS 정리`

---

### P3 — 폴리시 항목 (4건)

**[P3-A] `@keyframes auth-spin` 전역 스코프**
- 단일 앱에서는 문제없으나, CSS Modules 또는 마이크로프런트엔드 환경에서 이름 충돌 위험.
- **Recommendation:** 이름을 `auth-spinner-rotation`으로 구체화하거나 향후 CSS Modules 도입 시 로컬 스코프로 이동.

**[P3-B] `.auth-proof-card { max-width: 240px }` — px 단위 고정**
- 사용자 브라우저 텍스트 크기 200% 확대 시 카드 내부 텍스트가 좁아짐.
- **Recommendation:** `max-width: 15rem` (텍스트 크기와 함께 스케일링).

**[P3-C] `.auth-form { gap: 20px }` — 하드코딩 간격**
- `:root` 스페이싱 스케일에 `--s5` 미정의로 당시 임시 처리됨.
- **Recommendation:** `:root`에 `--s5: 20px` 추가 후 `gap: var(--s5)` 교체.

**[P3-D] `.auth-mobile-brand` 모바일 variant에서 `gap: 0`**
- 기본 flex 스타일에 `gap: 0`으로 설정됨. `margin-top: var(--s2)`는 `auth-mobile-brand__desc`에 있으나 명시적 gap이 0인 것은 의도인지 버그인지 불분명.
- **Recommendation:** `gap: var(--s2)`로 명시 또는 `gap: 0` 제거 후 desc의 `margin-top` 활용.

---

## Patterns & Systemic Issues

1. **`var(--text-3)` 대비 미달 — 시스템 전체 패턴:** `oklch(63% 0.008 152)` 값은 밝은 배경(`var(--surface)`, `var(--bg)`)에서 항상 WCAG AA 미달(~2.5:1). Auth 페이지만의 문제가 아니라 `text-3` 토큰 자체가 large text(18pt 이상)에만 유효한 수준. 향후 모든 화면에서 `var(--text-3)`를 small body text에 사용하면 동일 실패 반복.

2. **다크 패널 전경 토큰 부재:** `--dark-bg`, `--dark-bg-2` 배경 토큰은 있으나 그 위에 올라가는 전경(텍스트/보더) 토큰이 없음. 매번 인라인 OKLCH 리터럴로 보완. `--dark-text-1/2/3`, `--dark-border` 세트가 `:root`에 있어야 한다.

3. **`#fff` / `#000` in btn classes:** `.btn-primary`, `.btn-white` 등 전역 버튼 CSS에 raw hex 사용. DESIGN.md 원칙 위반이 auth뿐 아니라 전체 버튼 시스템에 걸쳐 있음.

---

## Positive Findings

1. **`--risk-critical-faint` 토큰 올바르게 참조** — 에러 배경에 `var(--risk-critical-faint)` 사용. 토큰이 `:root`에 정의(`oklch(97% 0.025 25)`)되어 있어 안전.
2. **`--gutter` 토큰 존재** — 반응형 media query에서 `var(--gutter)` 올바르게 사용. `clamp(var(--s6), 5vw, var(--s16))`로 유동 패딩.
3. **`.btn-lg` 터치 타겟 통과** — 계산상 ~54px (font-size 18px × line-height 1.4 + padding 0.8em×2). WCAG 44px 기준 통과.
4. **`aria-invalid` + `aria-describedby` 구현** — 에러 상태에서 스크린 리더가 필드-에러 메시지를 연결. `role="alert"` 병행 사용으로 이중 안내.
5. **`@media (prefers-reduced-motion: no-preference)` 스크롤 리빌** — 전역 reveal 애니메이션은 이미 guard 처리됨. auth 스피너만 미적용.
6. **`font: inherit` 리셋** — 모든 input/button이 body font를 상속. Pretendard Variable 일관 적용.
7. **TypeScript 0 errors** — 빌드 클린.

---

## Recommended Actions (Priority Order)

| Priority | Command | Context |
|----------|---------|---------|
| P1 | `/impeccable harden auth 접근성` | WCAG AA 대비 4건 일괄 수정: text-3, accent-on-dark, cite chip, label |
| P2 | `/impeccable animate auth 모션 접근성` | `prefers-reduced-motion` 스피너 guard |
| P2 | `/impeccable harden auth 포커스/헤딩` | `:focus-visible` 패턴, 모바일 h1 |
| P2 | `/impeccable extract auth 다크 토큰` | 인라인 OKLCH 리터럴 10개 → `--dark-text-*` 토큰화 |
| P2 | `/impeccable polish auth 데드코드` | `.auth-field__forgot` 제거, `#fff` → OKLCH |
| P3 | `/impeccable polish auth 간격` | `--s5` 토큰 추가, proof card max-width rem 전환 |
| Final | `/impeccable polish auth` | 전체 마무리 패스 |

> Re-run `/impeccable audit auth` after fixes to see score improve.
