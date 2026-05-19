---
name: PolyInsight
description: 학술 논문 PDF를 원문 기반 카드뉴스로 변환하는 연구자 도구
colors:
  forest-green:        "oklch(38% 0.14 152)"
  forest-green-deep:   "oklch(32% 0.14 152)"
  forest-green-wash:   "oklch(94% 0.035 152)"
  forest-green-ghost:  "oklch(97% 0.018 152)"
  canvas:              "oklch(99.8% 0.002 152)"
  canvas-warm:         "oklch(98% 0.005 152)"
  canvas-subtle:       "oklch(95.5% 0.009 152)"
  canvas-muted:        "oklch(92% 0.012 152)"
  border:              "oklch(89% 0.012 152)"
  border-subtle:       "oklch(93.5% 0.007 152)"
  ink-1:               "oklch(16% 0.008 152)"
  ink-2:               "oklch(44% 0.012 152)"
  ink-3:               "oklch(63% 0.008 152)"
  dark-slate:          "oklch(14% 0.04 152)"
  dark-slate-2:        "oklch(19% 0.04 152)"
  risk-critical:       "oklch(40% 0.16 25)"
  risk-critical-wash:  "oklch(97% 0.025 25)"
  risk-critical-border: "oklch(78% 0.10 25)"
  risk-high:           "oklch(42% 0.18 50)"
  risk-high-wash:      "oklch(97% 0.03 50)"
  risk-medium:         "oklch(45% 0.14 80)"
  risk-medium-wash:    "oklch(98% 0.02 80)"
  status-ok:           "oklch(34% 0.12 152)"
  status-ok-bg:        "oklch(93% 0.05 152)"
typography:
  display:
    fontFamily: "'Pretendard Variable', 'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif"
    fontSize: "clamp(2.625rem, 5.5vw + 0.75rem, 5rem)"
    fontWeight: 700
    lineHeight: 1.0
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "'Pretendard Variable', 'Pretendard', sans-serif"
    fontSize: "clamp(1.875rem, 3vw + 0.75rem, 2.875rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  title:
    fontFamily: "'Pretendard Variable', 'Pretendard', sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.025em"
  body:
    fontFamily: "'Pretendard Variable', 'Pretendard', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "-0.01em"
  label:
    fontFamily: "'Pretendard Variable', 'Pretendard', sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.03em"
rounded:
  sm: "6px"
  md: "10px"
  lg: "16px"
  xl: "20px"
spacing:
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  6: "24px"
  8: "32px"
  10: "40px"
  12: "48px"
  16: "64px"
components:
  button-primary:
    backgroundColor: "{colors.forest-green}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "10px 24px"
    typography: "{typography.label}"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.forest-green-deep}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "10px 24px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.forest-green}"
    rounded: "{rounded.md}"
    padding: "10px 24px"
  button-ghost-hover:
    backgroundColor: "{colors.forest-green-wash}"
    textColor: "{colors.forest-green}"
    rounded: "{rounded.md}"
    padding: "10px 24px"
  input-default:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-1}"
    rounded: "{rounded.sm}"
    padding: "10px 14px"
  card-surface:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.lg}"
    padding: "20px"
  modal-container:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.xl}"
    padding: "20px"
---

# Design System: PolyInsight

## 1. Overview

**Creative North Star: "The Academic Desk"**

PolyInsight는 연구자의 작업대다. 논문이 펼쳐져 있고, 형광펜이 그어져 있으며, 출처가 정확히 표기되어 있다. 이 시스템이 내리는 모든 시각적 결정은 하나의 질문으로 수렴한다: 이것이 연구자의 집중을 돕는가?

색상은 차분하고 틴팅이 일관적이다. 딥 포레스트 그린은 전형적인 SaaS 블루/퍼플을 의도적으로 반사하며, 학술지와 연구 환경의 색조를 연상시킨다. 모든 중성색은 hue 152로 미세하게 틴팅되어 — 순수한 회색이 아닌, 브랜드 색조가 스며든 화이트와 그레이 — 전체 인터페이스에 일관된 온도감을 준다.

위험도 시스템(CRITICAL / HIGH / MEDIUM / OK)은 이 디자인에서 단순한 UI 패턴이 아니다. 그것은 제품 철학 "수치가 신뢰다"의 시각적 구현이다. 빨강, 주황, 노랑, 초록의 신호등 체계는 장식이 아니라 책임의 표시다.

**Key Characteristics:**
- 모든 색상은 OKLCH, hue 152로 일관 틴팅 (검정도, 흰색도 순수하지 않다)
- 그림자는 상태에만 반응 — 기본 상태에서 모든 표면은 평평하다
- 타이포그래피 계층은 scale ratio ≥ 1.25, letter-spacing은 항상 음수
- 위험도 색상(25/50/80 hue)은 브랜드 hue와 의도적으로 대비된다
- 인터페이스 언어는 한국어 전용; 영문 기술 용어는 금지

---

## 2. Colors: The Forest-Tinted Palette

모든 색상은 동일한 hue(152)를 공유한다. 어두운 쪽은 채도를 높이고, 밝은 쪽은 채도를 낮춘다 — OKLCH의 감쇠 법칙을 따른다.

### Primary
- **딥 포레스트 그린** (`oklch(38% 0.14 152)`): 제품 전체의 유일한 액센트. 버튼, 링크, 활성 상태, 진행 표시에 사용. 전체 화면의 ≤10%만 차지한다.
- **포레스트 딥** (`oklch(32% 0.14 152)`): 버튼 hover 상태 전용. 독립적으로 등장하지 않는다.
- **포레스트 워시** (`oklch(94% 0.035 152)`): 선택된 항목 배경, 인라인 하이라이트. 액센트의 극도로 옅은 반향.
- **포레스트 고스트** (`oklch(97% 0.018 152)`): hover 피드백 중 가장 약한 단계.

### Neutral
- **캔버스** (`oklch(99.8% 0.002 152)`): 카드, 모달, 입력 필드의 표면. 순수한 흰색이 아닌, hue 152로 미세 틴팅.
- **캔버스 웜** (`oklch(98% 0.005 152)`): 페이지 배경. 캔버스보다 한 단계 어둡다.
- **캔버스 서틀** (`oklch(95.5% 0.009 152)`): 비활성 섹션, 내부 배경.
- **캔버스 뮤티드** (`oklch(92% 0.012 152)`): 구분선 영역, 입력 비활성 배경.
- **보더** (`oklch(89% 0.012 152)`): 카드 테두리, 인풋 테두리.
- **보더 서틀** (`oklch(93.5% 0.007 152)`): 내부 구분선.

### Text
- **잉크 1** (`oklch(16% 0.008 152)`): 본문 텍스트, 제목. 순수 검정이 아닌 틴팅된 짙은 색.
- **잉크 2** (`oklch(44% 0.012 152)`): 보조 텍스트, 레이블, 메타 정보.
- **잉크 3** (`oklch(63% 0.008 152)`): 비활성 텍스트, 플레이스홀더.

### Dark Layer
- **다크 슬레이트** (`oklch(14% 0.04 152)`): 랜딩 페이지 다크 섹션 배경. hue 152 틴팅이 두드러진다.
- **다크 슬레이트 2** (`oklch(19% 0.04 152)`): 다크 섹션 내부 서피스.

### Risk & Status
- **CRITICAL** (`oklch(40% 0.16 25)`): 검토 필수 항목. 원문 수치 불일치. 내보내기를 차단한다.
- **CRITICAL 워시** (`oklch(97% 0.025 25)`): CRITICAL 배경.
- **HIGH** (`oklch(42% 0.18 50)`): 주의 권장. 내보내기를 막지 않으나 경고한다.
- **MEDIUM** (`oklch(45% 0.14 80)`): 낮은 신뢰도. 정보 제공 목적.
- **OK** (`oklch(34% 0.12 152)`): 검증 완료. 브랜드 hue와 같아 — 안전은 브랜드 그린이다.

**The One Accent Rule.** 포레스트 그린은 주어진 화면의 ≤10%를 차지한다. 그것의 희소성이 신뢰를 만든다. 버튼과 링크가 아닌 곳에 accent color를 사용하는 것은 금지다.

**The Tinted Neutrals Rule.** 순수한 `#000`, `#fff`는 이 시스템에 존재하지 않는다. 모든 중성색은 hue 152로 틴팅된다. 순수 검정/흰색이 등장하면 디자인이 브랜드 팔레트에서 이탈했다는 신호다.

---

## 3. Typography

**Body/UI Font:** Pretendard Variable (Korean variable font, CDN or npm)
**Fallback chain:** Pretendard → Apple SD Gothic Neo → Noto Sans KR → system-ui, sans-serif

**Character:** Pretendard는 한국어에 최적화된 sans-serif 변체 폰트다. 자간을 음수(-0.01em ~ -0.025em)로 당겨 현대적이고 밀도 있는 인상을 만든다. 별도의 디스플레이 폰트는 없다 — Pretendard의 700 weight가 헤드라인과 UI 양쪽을 모두 담당한다.

### Hierarchy
- **Display** (700, `clamp(2.625rem, 5.5vw + 0.75rem, 5rem)`, lh 1.0, ls -0.025em): 랜딩 히어로 헤드라인 전용. 한 페이지에 하나.
- **Headline** (700, `clamp(1.875rem, 3vw + 0.75rem, 2.875rem)`, lh 1.1, ls -0.025em): 랜딩 섹션 제목. 에디터에는 나타나지 않는다.
- **Title** (700, `1.375rem`, lh 1.3, ls -0.025em): 카드 제목, 모달 헤더, 패널 섹션 이름.
- **Body** (400, `1rem`, lh 1.6, ls -0.01em): 콘텐츠 패널 텍스트, 설명, 카피. 최대 줄 길이 65–75ch.
- **Label** (600, `0.75rem`, lh 1, ls +0.03em, uppercase): 섹션 레이블, 뱃지 텍스트, 버튼. 대문자 적용 시 자간을 +0.03em으로 넓힌다.

**The Negative-Kerning Rule.** 제목과 헤딩의 letter-spacing은 항상 -0.025em. 본문은 -0.01em. 양수 자간은 uppercase label에서만 허용된다. 기본 자간(0)은 이 시스템에서 어색해 보인다.

**The Korean-First Rule.** `word-break: keep-all`이 전역 적용된다. 한국어 단어는 음절이 아닌 단어 단위로 줄바꿈된다. 이 규칙을 제거하면 좁은 화면에서 헤드라인이 깨진다.

---

## 4. Elevation

이 시스템은 **Flat-by-default**다. 기본 상태의 모든 표면은 그림자 없이 border와 배경색 차이만으로 구분된다. 그림자는 상태(hover, active, floating)에 대한 반응이다 — 장식이 아니다.

### Shadow Vocabulary
- **shadow-sm** (`0 2px 8px oklch(8% 0.01 152 / 0.07)`): 카드 hover 상태. 거의 느껴지지 않는 들어올림.
- **shadow-md** (`0 12px 32px oklch(8% 0.01 152 / 0.10)`): 드롭다운, 툴팁, 선택된 카드.
- **shadow-lg** (`0 16px 48px oklch(8% 0.01 152 / 0.18)`): 업로드 모달.
- **shadow-modal** (`0 24px 64px -12px rgba(15,20,40,0.30)`): 내보내기 모달, 가장 강한 그림자. 배경 오버레이와 함께 사용된다.

모든 그림자는 hue 152로 틴팅된 어두운 값을 사용한다. 순수 검정 그림자(`rgba(0,0,0,...)`)는 팔레트에서 이탈한 신호다.

**The State-Only Shadow Rule.** 카드는 기본 상태에서 border만 갖는다. hover 시 shadow-sm이 나타난다. 모달은 항상 shadow-modal을 갖는다. 이 세 단계 외의 그림자 깊이는 존재하지 않는다.

---

## 5. Components

### Buttons

버튼은 "확신 있는 행동 요청"이다. 크고 분명하고, hover 상태는 명확하다.

- **Shape:** 부드럽게 둥근 모서리 (10px radius). 캡슐(pill)도 직각(square)도 아닌 중간.
- **Primary:** 포레스트 그린 배경 + 캔버스 텍스트. 높이 40px, 패딩 10px 24px. Label 타이포(600, 0.75rem). hover 시 forest-green-deep으로 전환 (80ms ease-out).
- **Ghost:** 투명 배경 + 포레스트 그린 테두리 + 포레스트 그린 텍스트. hover 시 forest-green-wash 배경.
- **Disabled:** opacity 0.4, cursor not-allowed. 별도 색상 변경 없음.
- **Active:** `transform: translateY(1px)` — 눌리는 물리적 피드백.

### Cards / Containers

- **Corner Style:** 부드럽게 둥근 (16px radius). 내부 중첩 카드는 금지다.
- **Background:** 캔버스 (`oklch(99.8% 0.002 152)`).
- **Border:** 보더 색상 (`oklch(89% 0.012 152)`), 1px solid.
- **Shadow:** 기본 없음. hover 시 shadow-sm.
- **Internal Padding:** 20px (spacing 5). 내부 섹션 구분은 12-16px gap.

### Modals

모달은 중요한 전환점(업로드, 내보내기)에만 등장한다.

- **Container:** 캔버스 배경, 20px radius, shadow-modal, max-width 440px.
- **Overlay:** `oklch(14% 0.04 152 / 0.70)` 딤 + `blur(8px) saturate(120%)` backdrop.
- **Header:** `border-bottom: 1px solid border`. 제목은 Title 타이포.
- **RENDERING 상태:** 닫기 버튼 숨김 — 강제 종료 불가는 제품 철학이다.

### Inputs / Fields

- **Style:** 캔버스 배경, border 테두리, 6px radius.
- **Focus:** 포레스트 그린 2px solid outline, outline-offset 0. border-color도 forest-green으로 전환.
- **Error:** risk-critical-border 테두리, risk-critical-wash 배경.
- **Disabled:** opacity 0.5, cursor not-allowed.

### Risk Field Indicators

이 시스템의 시그니처 컴포넌트다. 카드 에디터의 콘텐츠 패널에서 모든 필드는 위험도 상태를 가진다.

- **CRITICAL:** risk-critical-border 테두리, risk-critical-wash 배경. 인라인 배너 + ActionBar 카운터 이중 노출. 내보내기를 차단한다.
- **HIGH:** risk-high-wash 배경, risk-high 텍스트. 경고만, 차단 없음.
- **MEDIUM:** risk-medium-wash 배경. 정보 제공.
- **OK:** status-ok 초록 아이콘. 액센트 컬러와 같은 hue — 검증된 것은 브랜드 색상이다.

### Navigation (Landing)

- 고정 높이 68px. `color-mix(in oklch, var(--bg) 82%, transparent)` 반투명 배경 + fallback 단색.
- 스크롤 시 `box-shadow: 0 1px 0 0 border-subtle`.
- 링크: 잉크2 기본, 잉크1 hover. transition 160ms.
- CTA 버튼: Primary button. 우측 끝 배치.

### Pipeline Progress (Upload Modal)

처리 중 화면의 시그니처 패턴. 학술 연구자의 불안을 제거하는 것이 목적이다.

- 단계 레이블(S1-S8)은 사용자 언어로 번역되어 표시된다. 기술 용어(Playwright, pdfplumber 등) 노출 금지.
- 완료 단계: status-ok 체크. 진행 단계: 스피너 + 포레스트 그린. 대기 단계: 잉크3.
- 전체 진행 바: forest-green fill, 캔버스 뮤티드 트랙.

---

## 6. Do's and Don'ts

### Do:
- **Do** 모든 색상에 OKLCH를 사용한다. 중성색은 반드시 hue 152로 틴팅한다.
- **Do** 그림자는 상태 변화(hover, modal 진입)에만 사용한다. 정적 카드에 그림자를 주지 않는다.
- **Do** 타이포그래피 letter-spacing은 항상 음수(-0.01em ~ -0.025em). 제목은 -0.025em 고정.
- **Do** `word-break: keep-all`을 전역 적용한다. 한국어 줄바꿈은 단어 단위다.
- **Do** 위험도 색상(CRITICAL/HIGH/MEDIUM/OK)을 인라인 필드와 ActionBar 카운터 양쪽에 이중 노출한다.
- **Do** 처리 중 화면에서 기술 용어(Playwright, S1-S8 코드 등)를 한국어 사용자 언어로 번역한다.
- **Do** Primary 버튼 active 상태에 `transform: translateY(1px)`를 적용한다 — 물리적 피드백.
- **Do** `color-mix(in oklch, var(--bg) 82%, transparent)` 배경에 항상 단색 fallback을 앞에 선언한다.

### Don't:
- **Don't** 순수 `#000` 또는 `#fff`를 사용한다. 모든 검정/흰색은 hue 152로 틴팅되어야 한다.
- **Don't** 포레스트 그린 액센트를 화면의 10% 이상에 사용한다. 희소성이 신뢰를 만든다.
- **Don't** 기능 목록을 나열하는 AI 랜딩 페이지 구조를 쓴다 (Concept Over Flow). 3단계 워크플로우가 주인공이다.
- **Don't** 감성 위주 브랜드 랜딩 스타일을 쓴다 (Form Over Function). 비주얼이 생산성보다 앞서면 안 된다.
- **Don't** 단발성 기능 블록 나열 구조를 쓴다 (Feature Isolation). 사용자 여정의 연속성이 끊기면 안 된다.
- **Don't** 전형적인 SaaS 크림·퍼플 배경을 쓴다 (Intercom, HubSpot 류).
- **Don't** AI 스타트업 과장 스타일을 쓴다. 네온, 다크모드 기본, "혁신" 남발 금지.
- **Don't** 모달 UI에서 관료제 스타일(회색 배경, 구식 폼 필드)을 쓴다.
- **Don't** 랜딩과 동떨어진 스타일의 모달을 만든다. 모달은 랜딩과 동일한 디자인 언어를 써야 한다.
- **Don't** `border-left`를 1px 초과 컬러 액센트 스트라이프로 사용한다. 배경 틴팅이나 전체 테두리로 대체한다.
- **Don't** 그라디언트 텍스트(`background-clip: text`)를 쓴다. 색상은 단일 고형(solid)이어야 한다.
- **Don't** 글래스모피즘을 장식으로 사용한다. overlay-blur는 모달 배경에서 기능적 목적으로만 쓴다.
- **Don't** CSS layout 속성(width, height, margin, padding)을 직접 트랜지션한다. `transform`과 `opacity`만 animate한다.
- **Don't** `@theme` 블록이나 CSS 변수에 hex/rgb 색상값을 직접 쓴다. 반드시 OKLCH `var()` 참조.
