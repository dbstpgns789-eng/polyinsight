---
name: PolyInsight
description: 학술 논문 PDF를 원문 기반 카드뉴스로 변환하는 연구자 도구
colors:
  # Brand Accent (Max 10% usage)
  forest-green:        "oklch(38% 0.14 152)"
  forest-green-deep:   "oklch(32% 0.14 152)"
  forest-green-wash:   "oklch(94% 0.035 152)"
  forest-green-ghost:  "oklch(97% 0.018 152)"

  # Neutral Surfaces (Tinted with Hue 152)
  canvas:              "oklch(99.8% 0.002 152)"
  canvas-warm:         "oklch(98% 0.005 152)"
  canvas-subtle:       "oklch(95.5% 0.009 152)"
  canvas-muted:        "oklch(92% 0.012 152)"
  dark-slate:          "oklch(14% 0.04 152)"

  # Borders
  border:              "oklch(89% 0.012 152)"
  border-subtle:       "oklch(93.5% 0.007 152)"

  # Typography Tokens (Semantic mapping inside brackets)
  ink-1:               "oklch(16% 0.008 152)" # [ink-primary] Primary Text / Headings
  ink-2:               "oklch(44% 0.012 152)" # [ink-secondary] Body / Labels
  ink-3:               "oklch(63% 0.008 152)" # [ink-tertiary] Muted / Captions

  # Status Signals
  risk-critical:       "oklch(40% 0.16 25)"
  risk-high:           "oklch(42% 0.18 50)"
  risk-medium:         "oklch(45% 0.14 80)"
  status-ok:           "oklch(34% 0.12 152)"
---

# PolyInsight Design System & Component Rules

## 1. Layout Architecture (Viewport-Fit)
- **전체 화면 제약 (`Screen Constraint`):** 대시보드는 브라우저 줌 100% 상태에서 세로 스크롤바가 발생하지 않는 `h-screen overflow-hidden`을 기본 뼈대로 삼는다.
- **3단 워크플로우 분할:** 상단 바(Topbar) 아래 공간은 [좌측 검토 패널] - [중앙 편집 공간] - [우측 디자인 설정]의 3단 레이아웃으로 고정되며, 각 패널은 독립적인 내부 스크롤(`overflow-y-auto`)을 가져야 한다.

## 2. Fluid Geometry & Component Specs
- **가변형 세로 높이 (Fluid Height):** 컴포넌트의 높이를 `px` 고정값으로 묶는 행위를 지양한다. 화면 해상도(특히 13~14인치 노트북 환경)에 따라 레이아웃이 터지지 않고 유기적으로 축소(Scale-down)될 수 있도록 가변성을 확보한다.
- **버튼 규격:** 버튼은 고정 높이 대신 상하 패딩(`py-2` ~ `py-2.5`)을 우선하여 자연스러운 높이를 형성하되, 세로축 압축 대응을 위해 최소/최대 제약조건(**`min-h-[36px] max-h-[40px]`**) 범위를 준수한다. 모서리 곡률은 `10px (rounded-btn)`로 처리한다.
- **카드 및 컨테이너 규격:** 모서리 곡률은 `16px (rounded-card)`을 일관되게 적용한다.
- **요소 간 간격 제어:** 컴포넌트 자체의 크기를 줄이기 전에 요소 간의 간격(`gap`, `space-y-*`)을 유연하게 조절하여 세로 오버플로우를 원천 차단한다.

## 3. Typography Rules
- **전역 한국어 줄바꿈:** 한국어 가독성을 위해 텍스트가 줄바꿈될 때 단어가 쪼개지지 않도록 **`word-break: keep-all;`**을 전역 또는 컴포넌트 루트에 반드시 선언한다.
- **자간 (Letter-spacing) 규칙:** - 국문 헤드라인 및 타이틀 계층: **`-0.025em`** 고정 (밀도감 확보)
  - 일반 본문 및 피드 계층: **`-0.01em`** 고정
  - 영문 대문자 영문 메타데이터 레이블: **`+0.03em`** (가독성을 위한 확장 자간 허용)

## 4. UI Depth & Shadows
- **정적 그림자 배제:** 시스템의 기본 서피스는 플랫(Flat)함을 원칙으로 한다. 정적 카드나 패널에 무분별한 그림자(`shadow-*`)를 주지 않으며, 테두리(`border-subtle`) 선으로 레이어를 분리한다.
- **예외적 그림자 허용:** 그림자는 오직 물리적 깊이감 표현이 필요한 다음 상태에서만 허용한다.
  - 마우스 호버(`hover:shadow-md`) 상태
  - 모달/팝업 컴포넌트 진입 상태
  - 중앙 편집창 내에서 떠 있는 형태를 유지하는 메인 카드뉴스 프리뷰 캔버스

---

## Do's & Don't's Quick Reference

### Do:
- **Do** 모든 중성색과 서피스는 OKLCH Hue 152로 틴팅한다.
- **Do** 위험도 색상(CRITICAL/HIGH/MEDIUM/OK)을 인라인 상태 표시 칩과 프로그레스 영역 양쪽에 이중 노출한다.
- **Do** Primary 버튼이 클릭(active)될 때 `transform: translateY(1px)` 효과를 주어 물리적 타격 피드백을 제공한다.
- **Do** 가변형 구조 레이아웃을 위해 `flex-1`, `shrink-0`, `min-h-0` 유틸리티 클래스를 명확히 명시한다.

### Don't:
- **Don't** 순수 `#000` 또는 `#fff`를 사용한다. 시스템 내 화이트와 블랙은 언제나 틴팅된 중성색 토큰으로 대체한다.
- **Don't** 포레스트 그린 액센트 컬러를 전체 화면 면적의 10% 이상 남용하지 않는다. 희소성이 전문적인 신뢰감을 만든다.
- **Don't** 감성 위주의 브랜드 랜딩 스타일(Form Over Function)을 지양하고, 연구 데이터 검토를 위한 3단계 워크플로우 기능(Form Follows Function)을 중심에 둔다.