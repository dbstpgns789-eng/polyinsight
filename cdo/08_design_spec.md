# 08 · PolyInsight 카드뉴스 디자인 스펙

> PolyInsight Design Spec v2.0 | 2026-05-11
> KITECH 샘플 레퍼런스 기반 → PolyInsight 독자 디자인 시스템으로 재정의
>
> 분석 샘플: 9개 에피소드 (What if Technology 13·15·16화, 혈당센서, What if Technology 4·11화, 생기원 기술이야기 3·4·9화)
> 이 문서의 수치는 1080×1080px 픽셀 기준. (추정) 표기는 고해상도 원본 미확보 항목.

---

## 1. 개요

### 1-1. 카드 포맷

| 항목 | 값 |
|------|-----|
| 캔버스 크기 | 1080 × 1080 px (정방형) |
| 출력 포맷 | PNG (알파 없음), JPEG |
| 색상 공간 | sRGB |
| 장수 | 5~11장 (에피소드별 가변, 파이프라인 기본: 5장) |
| 종횡비 | 1 : 1 (Instagram 피드, 네이버 블로그 카드뉴스 공통) |

### 1-2. 사용 채널

- **네이버 블로그** (주 채널 — 포스트 내 이미지 슬라이드)
- **인스타그램 피드** (정방형 슬라이드)
- **내부 SNS 배포용** (카카오채널 등 예상)

### 1-3. 시리즈 분류 및 디자인 버전

PolyInsight가 레퍼런스로 삼은 시리즈는 3종이며, 각각 독립적인 레이아웃 패턴을 가진다.
PolyInsight 출력물은 이 시리즈에 종속되지 않으며, 아래는 학습 레퍼런스 분류다.

| 시리즈 ID | 시리즈명 | 대표 샘플 | 디자인 버전 | 비고 |
|-----------|----------|-----------|-------------|------|
| `WIT_V2` | What if Technology (현버전) | 13화, 15화, 16화 | 2025+ | **레이아웃 레퍼런스 주축** |
| `WIT_V1` | What if Technology (구버전) | 4화, 11화 | ~2024 | 레거시, 참고용 |
| `KITECH_STORY_DARK` | 생기원 기술 이야기 (다크 네온) | HMF 9화, 3D 4화 | 2025 | |
| `KITECH_STORY_PHOTO` | 생기원 기술 이야기 (실사버전) | 에틸렌 3화 | 2025 | 실사 사진 배경 |

> **S7 구현 우선순위**: WIT_V2 기반 Type A~G → Type H·I·J (프로덕트 단계)

### 1-4. 디자인 시스템 원칙

이 디자인 시스템은 특정 기관(KITECH)에 종속되지 않는다.

**원칙 1: 레퍼런스와 결과물을 분리한다**
- KITECH 샘플 = 레이아웃 패턴, 가독성 원칙, 정보 계층 학습용
- PolyInsight 출력 = 독자 디자인 토큰 적용

**원칙 2: 토큰은 역할 기반이다**
- `--surface-base`, `--text-primary`, `--theme-primary` 등
- KITECH 시리즈명, 에피소드 번호 기반 토큰 없음

**원칙 3: 테마는 동적으로 주입된다**
- `--theme-primary`는 논문 Job마다 다름
- S6 JSON → S7 렌더링 시 CSS 변수로 주입

**원칙 4: 기관 로고와 브랜드는 파라미터다**
- `org_logo_url`, `org_name`, `research_dept`는 사용자 입력값
- 디자인 시스템 레벨에서 고정되지 않음

---

## 2. 색상 시스템 (Design Tokens)

### 2-1. Layer 1 — Global Tokens (`_shared.css`에 정의, 고정)

```css
:root {
  /* Surface */
  --surface-base:        #FFFFFF;
  --surface-card:        #F8F9FA;
  --surface-overlay:     rgba(0, 0, 0, 0.45);

  /* Text */
  --text-primary:        #212529;
  --text-secondary:      #495057;
  --text-caption:        #868E96;
  --text-on-dark:        #FFFFFF;
  --text-on-dark-muted:  rgba(255, 255, 255, 0.80);

  /* Component */
  --badge-bg-light:      rgba(255, 255, 255, 0.88);
  --badge-border-light:  rgba(0, 0, 0, 0.12);
  --shadow-card:         0 4px 16px rgba(0,0,0,0.08), 0 16px 48px rgba(0,0,0,0.06);
  --radius-card:         20px;
  --radius-pill:         100px;

  /* Theme slots — S7이 per-job으로 주입. 아래는 fallback only */
  --theme-primary:       #2563EB;
  --theme-dark:          #1A4C96;
}
```

### 2-2. Layer 2 — Per-Job Theme Tokens (S6 JSON → S7 주입)

S6 JSON의 `theme` 객체:

```json
{
  "theme": {
    "primary": "#3BAF6B",
    "dark":    "#217A47"
  }
}
```

S7 렌더링 시 HTML `<style>` 태그에 주입:

```css
/* S7이 각 Job마다 동적으로 생성하는 블록 */
:root {
  --theme-primary: {{ theme.primary }};
  --theme-dark:    {{ theme.dark }};
}
```

> 관찰 근거: 13화 커버 삼각형(녹색), 15화 커버 삼각형+아이콘(청록), 16화 커버(앰버).
> 정확한 hex는 원본 Figma 파일 없이 시각 추정. 실제 구현 시 픽셀 추출로 재측정 권장.

---

## 3. 타이포그래피 시스템

### 3-1. 폰트 패밀리

```css
/* 제목/본문 공통 — Pretendard 우선 */
--font-display: 'Pretendard', 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
--font-body:    'Pretendard', 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
```

> 관찰: 샘플 전체에서 산세리프 고딕 사용 확인. 커버 초대형 제목의 굵기(900)와
> 날카로운 직선 스트로크 패턴 → Pretendard ExtraBold 또는 Noto Sans KR Black (추정).
> 웹폰트 구현 시: `font-family: 'Pretendard', 'Noto Sans KR', sans-serif; font-weight: 900;` 우선 사용.

### 3-2. 텍스트 계층별 스펙

```
캔버스 기준 1080px. 모든 px 값은 출력 해상도 기준.
```

| 레벨 | 역할 | font-size | font-weight | line-height | letter-spacing | 색상 | 사용 맥락 |
|------|------|-----------|-------------|-------------|----------------|------|-----------|
| D1 | 커버 초대형 제목 1행 | 100–120px | 900 | 1.0–1.1 | -0.02em | `var(--text-on-dark)` or `var(--theme-primary)` | 커버 메인 타이틀 상단행 |
| D2 | 커버 초대형 제목 2행 | 80–100px | 900 | 1.0–1.1 | -0.02em | `var(--text-on-dark)` | 커버 메인 타이틀 하단행 |
| H1 | 섹션 대표 헤드라인 | 52–64px | 800 | 1.2 | -0.01em | `var(--text-primary)` or `var(--text-on-dark)` | 본문 카드 상단 제목 |
| H2 | 소제목 | 38–46px | 700 | 1.3 | -0.01em | `var(--text-primary)` or `var(--theme-primary)` | 카드 내 소제목 |
| H3 | 강조 키워드 | 28–36px | 700 | 1.3 | 0 | `var(--theme-primary)` | 인라인 강조, 배지 |
| B1 | 본문 | 24–28px | 400–500 | 1.6–1.7 | 0 | `var(--text-primary)` | 설명 텍스트 |
| B2 | 보조 본문 | 20–24px | 400 | 1.6 | 0 | `var(--text-secondary)` | 부연 설명 |
| C1 | 캡션/배지 | 18–22px | 500–600 | 1.4 | 0.01em | `var(--text-secondary)` | pill 배지, 출처 |
| N1 | 수치 강조 | 64–80px | 900 | 1.0 | -0.02em | `var(--theme-primary)` or `var(--text-on-dark)` | Type C 그리드 숫자 |
| N2 | 수치 단위 | 28–36px | 700 | 1.0 | 0 | `var(--text-on-dark)` or `var(--theme-primary)` | 수치 옆 단위 텍스트 |

#### CSS 클래스 예시

```css
.text-d1 {
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 110px;
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--text-on-dark);
}

.text-h1 {
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 56px;
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.01em;
  color: var(--text-primary);
}

.text-b1 {
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 26px;
  font-weight: 400;
  line-height: 1.65;
  letter-spacing: 0;
  color: var(--text-primary);
}

.text-n1 {
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 72px;
  font-weight: 900;
  line-height: 1.0;
  letter-spacing: -0.02em;
}
```

---

## 4. 간격 및 레이아웃 시스템

### 4-1. 캔버스 & 안전 영역

```
┌─────────────────────────────────────────────────────┐
│              캔버스: 1080 × 1080 px                  │
│  ┌───────────────────────────────────────────────┐  │
│  │           Safe Zone (960 × 960 px)            │  │
│  │  margin: 60px 상/하/좌/우 (추정)               │  │
│  │                                               │  │
│  │  콘텐츠 영역: 960 × 960 px                    │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

```css
.card-canvas {
  width: 1080px;
  height: 1080px;
  position: relative;
  overflow: hidden;
}

.card-safe-zone {
  position: absolute;
  inset: 60px;           /* 상하좌우 60px 여백 (추정) */
  /* = top:60px; right:60px; bottom:60px; left:60px */
}
```

> 관찰: 13화 카드들의 콘텐츠 배치를 통해 가장자리 여백 최소 50–70px 확인 (추정 60px).
> 로고·배지 등 일부 요소는 safe zone 외부(캔버스 모서리)에 접하는 경우 있음.

### 4-2. 스페이싱 토큰

```css
:root {
  --space-xs:   8px;
  --space-sm:  16px;
  --space-md:  24px;
  --space-lg:  40px;
  --space-xl:  60px;
  --space-2xl: 80px;
  --space-3xl: 120px;
}
```

### 4-3. 레이아웃 그리드

```css
/* 2컬럼 그리드 (Type D, C 사용) */
/* padding 없음 — .card-safe-zone이 이미 60px inset 처리 */
.grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

/* 2×2 그리드 (Type C 4셀) */
.grid-2x2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 24px;
}

/* 3컬럼 그리드 (Type C 3셀) */
.grid-3col {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 24px;
}
```

---

## 5. 레이아웃 타입 스펙 (10종)

### 5-0. 레이아웃 타입 선택 방식

`layout_type`은 별도 필드로 선택하지 않는다.
**S6가 카드 데이터를 어떤 Pydantic 모델로 채웠느냐가 곧 레이아웃을 결정한다.**

| 카드 Pydantic 모델 | 렌더링 레이아웃 |
|-------------------|----------------|
| `CoverCard` | Type A (Card 1 고정) |
| `HookCard` | Type E |
| `TextCard` | Type B (범용 기본값) |
| `StatGridCard` | Type C (수치 3개 이상일 때) |
| `CompareCard` | Type D (비교 구조일 때) |
| `SpecCard` | Type F (제품/실험 사진 있을 때) |
| `FlowCard` | Type G (단계 프로세스 3개 이상일 때) |
| `ClosingCard` | Type K (Card 5 고정) |

**S6 선택 기준** (S6 프롬프트에도 동일하게 명시):

```
- 카드 콘텐츠에 수치 데이터 3개 이상   → StatGridCard
- 카드 콘텐츠에 단계 프로세스 3개 이상  → FlowCard
- 카드 콘텐츠에 비교 구조 (기존 vs 신기술) → CompareCard
- 카드 콘텐츠에 제품/실험 결과 사진 필요  → SpecCard
- 위 조건 없으면                        → TextCard (기본값)
```

---

### Type A — 표지형 (커버)

> [MVP 구현 대상]

**사용 슬롯**: Card 1 (에피소드 커버, `CoverCard`)
**관찰 샘플**: WIT_V2 13화 Card 1, 15화 Card 1, 16화 Card 1

```
┌──────────────────────────────────┐
│  [시리즈 배지: "N화"] ← top-center, y=80px
│                                  │
│   초대형 타이틀 텍스트             │ ← 중앙 상단 ~y=300–480px
│   (D1 + D2 계층)                 │
│                                  │
│                    ┌──삼각형──┐   │ ← bottom-right
│                    │  icon   │   │    540×540px (추정), corner 배치
│                    └─────────┘   │
│  [org 로고] [슬로건]              │ ← bottom, y=980px
└──────────────────────────────────┘
```

```css
.layout-type-a {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: var(--surface-base);
  overflow: hidden;
}

/* 배경 사진 (있는 경우) */
.layout-type-a .bg-photo {
  position: absolute;
  inset: 0;
  object-fit: cover;
  filter: brightness(0.65);
  z-index: 0;
}

/* 시리즈 배지 */
.layout-type-a .series-badge {
  position: absolute;
  top: 72px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--badge-bg-light);
  border: 1.5px solid var(--badge-border-light);
  border-radius: var(--radius-pill);
  padding: 12px 32px;
  font-size: 22px;
  font-weight: 600;
  white-space: nowrap;
  z-index: 10;
}

/* 메인 타이틀 */
.layout-type-a .main-title {
  position: absolute;
  left: 60px;
  top: 260px;               /* (추정) */
  width: 680px;
  z-index: 10;
}

/* 하단 삼각형 기하도형 — 우하단 고정 */
.layout-type-a .triangle-accent {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 540px;             /* (추정) */
  height: 540px;
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
  background: var(--theme-primary);
  z-index: 5;
}

/* 삼각형 내 아이콘 */
.layout-type-a .triangle-icon {
  position: absolute;
  bottom: 60px;
  right: 60px;
  width: 240px;             /* (추정) */
  height: 240px;
  z-index: 6;
  opacity: 0.90;
}

/* 하단 브랜드 바 */
.layout-type-a .brand-bar {
  position: absolute;
  bottom: 32px;
  left: 60px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-on-dark);
}
```

**필수 데이터 필드**: `episode_badge`, `main_title_line1`, `main_title_line2`, `theme_primary`, `icon_image` (선택)

---

### Type B — 헤더+카드형

> [MVP 구현 대상]

**사용 슬롯**: Card 2–5 (본문 설명 카드, `TextCard`)
**관찰 샘플**: WIT_V2 13화 Card 2~5, 15화 Card 2~5, 16화 Card 2~5

```
┌──────────────────────────────────┐
│  배경 컬러 or 사진 (테마 or 흰색)  │
│                                  │
│  ┌────────────────────────────┐  │ ← top: 100–140px
│  │  [섹션 헤더 텍스트 H1/H2]  │  │   left/right: 60px
│  │                            │  │   border-radius: 20px
│  │  본문 텍스트 (B1)           │  │   padding: 48px 52px
│  │  • 리스트 항목 or 단락     │  │   background: white
│  │                            │  │   box-shadow: 있음
│  └────────────────────────────┘  │
│                                  │
└──────────────────────────────────┘
```

```css
.layout-type-b {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: var(--surface-base);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
}

.layout-type-b .content-card {
  width: 960px;
  background: var(--surface-base);
  border-radius: var(--radius-card);
  padding: 52px 56px;
  box-shadow: var(--shadow-card);
  position: relative;
  z-index: 5;
}

.layout-type-b .section-header {
  font-size: 52px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 28px;
  color: var(--text-primary);
}

.layout-type-b .section-header .accent {
  color: var(--theme-primary);
}

.layout-type-b .body-text {
  font-size: 26px;
  font-weight: 400;
  line-height: 1.65;
  color: var(--text-primary);
}
```

**필수 데이터 필드**: `section_title`, `body_text` (최대 200자 권장), `accent_keyword` (선택)

---

### Type C — 그리드형

> [MVP 구현 대상]

**사용 슬롯**: 성과/수치 강조 카드 (`StatGridCard`)
**관찰 샘플**: WIT_V2 13화 Card 7, 15화 Card 5 (추정)

```
┌──────────────────────────────────┐
│  [섹션 제목 H1]                  │
│                                  │
│  ┌──────────┐  ┌──────────┐     │ ← 2×2 또는 1×3 그리드
│  │  수치 N1 │  │  수치 N1 │     │   각 셀: ~420×300px (2×2)
│  │  단위 N2 │  │  단위 N2 │     │
│  │  설명 C1 │  │  설명 C1 │     │
│  └──────────┘  └──────────┘     │
│  ┌──────────┐  ┌──────────┐     │
│  │  수치 N1 │  │  수치 N1 │     │
│  └──────────┘  └──────────┘     │
└──────────────────────────────────┘
```

```css
.layout-type-c {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: var(--surface-base);
  padding: 80px 60px;
  display: flex;
  flex-direction: column;
}

.layout-type-c .section-title {
  font-size: 52px;
  font-weight: 800;
  margin-bottom: 40px;
  color: var(--text-primary);
}

.layout-type-c .grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  flex: 1;
}

.layout-type-c .stat-cell {
  background: var(--surface-card);
  border-radius: 16px;
  border-left: 6px solid var(--theme-primary);
  padding: 36px 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.layout-type-c .stat-value {
  font-size: 72px;
  font-weight: 900;
  line-height: 1.0;
  color: var(--theme-primary);
}

.layout-type-c .stat-unit {
  font-size: 30px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-left: 6px;
}

.layout-type-c .stat-label {
  font-size: 22px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-top: 8px;
}
```

**필수 데이터 필드**: `section_title`, `stats[]` (각: `value`, `unit`, `label`) — 최대 4개

---

### Type D — 비교형

> [MVP 구현 대상]

**사용 슬롯**: 기존 방식 vs 신기술 비교 (`CompareCard`)
**관찰 샘플**: 혈당 센서 카드 (기존 공정 vs 레이저 방식)

```
┌──────────────────────────────────┐
│  [비교 섹션 제목]                  │
│                                  │
│  ┌─────────┐    ┌─────────┐     │ ← 좌우 카드 각 460px (추정)
│  │ 비교A   │ vs │ 비교B   │     │   gap: 40px
│  │ (기존)  │    │ (신기술) │     │
│  │         │    │         │     │
│  │ 내용 B1 │    │ 내용 B1 │     │
│  └─────────┘    └─────────┘     │
└──────────────────────────────────┘
```

```css
.layout-type-d {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: var(--surface-base);
  padding: 80px 60px;
  display: flex;
  flex-direction: column;
}

.layout-type-d .compare-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 0;
  align-items: start;
  flex: 1;
}

.layout-type-d .compare-card {
  background: var(--surface-card);
  border-radius: 16px;
  padding: 40px 36px;
}

.layout-type-d .compare-card.highlight {
  background: var(--theme-primary);
  color: var(--text-on-dark);
}

.layout-type-d .vs-divider {
  width: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 900;
  color: #adb5bd;
}
```

**필수 데이터 필드**: `section_title`, `compare_left`, `compare_right`, `vs_label` (선택)

---

### Type E — 전면텍스트형

> [MVP 구현 대상]

**사용 슬롯**: 훅/감성 메시지 카드 (주로 Card 2, `HookCard`)
**관찰 샘플**: WIT_V2 13화 Card 2 (스마트팜 문제 제기), 에틸렌 3화 Card 2

```
┌──────────────────────────────────┐
│  [배경 사진 + 오버레이]            │ ← 전체 배경
│                                  │
│                                  │
│    대형 훅 텍스트                 │ ← 중앙 또는 상단
│    (H1 또는 D1/D2 혼용)          │
│                                  │
│    부제/설명 (B1)                 │
│                                  │
└──────────────────────────────────┘
```

```css
.layout-type-e {
  position: relative;
  width: 1080px;
  height: 1080px;
  overflow: hidden;
}

.layout-type-e .bg-photo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.layout-type-e .overlay {
  position: absolute;
  inset: 0;
  background: var(--surface-overlay);
  z-index: 1;
}

.layout-type-e .content {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 80px 60px;
}

.layout-type-e .hook-text {
  font-size: 62px;
  font-weight: 900;
  line-height: 1.2;
  color: var(--text-on-dark);
  margin-bottom: 24px;
}

.layout-type-e .sub-text {
  font-size: 28px;
  font-weight: 400;
  line-height: 1.6;
  color: var(--text-on-dark-muted);
}
```

**필수 데이터 필드**: `hook_text`, `bg_photo` (선택), `sub_text` (선택)

---

### Type F — 스펙형 (제품 사진 임베드)

> [MVP 구현 대상]

**사용 슬롯**: 기술 결과물/제품 설명 카드 (`SpecCard`)
**관찰 샘플**: 3D프린팅 4화 Card 5 (고압용기 사진 2장 그리드), 혈당 센서 Card

```
┌──────────────────────────────────┐
│  [섹션 제목 H1]                  │
│                                  │
│  ┌──────────────────────────┐   │
│  │  제품/결과 사진           │   │
│  │  (단일 or 2열 사진 그리드) │   │
│  └──────────────────────────┘   │
│                                  │
│  수치 강조 블록 or 설명 텍스트     │
└──────────────────────────────────┘
```

```css
.layout-type-f {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: var(--surface-base);
  padding: 80px 60px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.layout-type-f .product-image-wrap {
  flex: 1;
  border-radius: 16px;
  overflow: hidden;
}

.layout-type-f .product-image-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 2열 사진 그리드 */
.layout-type-f .photo-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  flex: 1;
}

.layout-type-f .spec-highlight {
  background: var(--surface-card);
  border-radius: 12px;
  padding: 24px 32px;
  font-size: 28px;
  font-weight: 700;
  color: var(--theme-primary);
}
```

**필수 데이터 필드**: `section_title`, `product_photo[]` (1~2장), `highlight_stat` (선택)

---

### Type G — 플로우형 (수직 단계 다이어그램)

> [MVP 구현 대상]

**사용 슬롯**: 프로세스/원리 설명 카드 (`FlowCard`)
**관찰 샘플**: 혈당 센서 Card (레이저 공정 ①②③④), WIT_V2 13화 (로봇 작동 단계)

```
┌──────────────────────────────────┐
│  [섹션 제목 H1]                  │
│                                  │
│  ① [단계 제목] ────────────────  │ ← 각 단계 row: h~180px
│     설명 텍스트 B1               │   좌측 번호 원형: 64px
│                                  │
│  ② [단계 제목] ────────────────  │
│     설명 텍스트 B1               │
│                                  │
│  ③ [단계 제목] ────────────────  │
│     설명 텍스트 B1               │
└──────────────────────────────────┘
```

```css
.layout-type-g {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: var(--surface-base);
  padding: 80px 60px;
  display: flex;
  flex-direction: column;
}

.layout-type-g .flow-list {
  display: flex;
  flex-direction: column;
  gap: 28px;
  flex: 1;
}

.layout-type-g .flow-item {
  display: flex;
  align-items: flex-start;
  gap: 24px;
}

.layout-type-g .step-number {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--theme-primary);
  color: var(--text-on-dark);
  font-size: 26px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.layout-type-g .step-content {
  flex: 1;
  padding-top: 8px;
}

.layout-type-g .step-title {
  font-size: 34px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.layout-type-g .step-desc {
  font-size: 24px;
  font-weight: 400;
  line-height: 1.6;
  color: var(--text-secondary);
}
```

**필수 데이터 필드**: `section_title`, `steps[]` (각: `title`, `desc`) — 2~4개

---

### Type H — 다크 네온 커버

> [MVP 제외 — 프로덕트 단계]

**사용 슬롯**: Card 1 (다크 시리즈 커버)
**관찰 샘플**: HMF 9화 Card 1, 3D프린팅 4화 Card 1, 에틸렌 3화 Card 1

```css
.layout-type-h {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: #080C18;   /* 극어두운 네이비-블랙 (추정) */
  overflow: hidden;
}

.layout-type-h .bg-photo {
  position: absolute;
  inset: 0;
  object-fit: cover;
  opacity: 0.30;
  z-index: 0;
}

.layout-type-h .series-pill {
  position: absolute;
  top: 72px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.12);
  border: 1.5px solid rgba(255, 255, 255, 0.30);
  border-radius: var(--radius-pill);
  padding: 12px 36px;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-on-dark);
  white-space: nowrap;
  z-index: 10;
}

.layout-type-h .main-title-wrap {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10;
  width: 900px;
}

/* --neon-color: 에피소드별 별도 주입 (예: #00FFC8, #7B5FFF) */
.layout-type-h .title-accent {
  font-size: 100px;
  font-weight: 900;
  color: var(--neon-color);
  line-height: 1.0;
}

.layout-type-h .title-main {
  font-size: 80px;
  font-weight: 900;
  color: var(--text-on-dark);
  line-height: 1.1;
}

.layout-type-h .sub-pill {
  display: inline-block;
  margin-top: 24px;
  background: rgba(255, 255, 255, 0.14);
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: var(--radius-pill);
  padding: 10px 28px;
  font-size: 22px;
  font-weight: 500;
  color: var(--text-on-dark-muted);
}
```

---

### Type I — 다크 네온 콘텐츠 박스

> [MVP 제외 — 프로덕트 단계]

**사용 슬롯**: Card 2–7 (다크 시리즈 본문)
**관찰 샘플**: HMF 9화 Card 2~6, 3D프린팅 4화 Card 2~7

```css
.layout-type-i {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: #080C18;
  padding: 80px 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.layout-type-i .neon-box {
  border: 2px solid var(--neon-color);
  border-radius: var(--radius-card);
  padding: 52px 56px;
  background: rgba(255, 255, 255, 0.04);
  box-shadow:
    0 0 20px rgba(var(--neon-color-rgb), 0.15),
    inset 0 0 40px rgba(var(--neon-color-rgb), 0.05);
}

.layout-type-i .box-title {
  font-size: 48px;
  font-weight: 800;
  color: var(--text-on-dark);
  margin-bottom: 24px;
}

.layout-type-i .box-title .accent {
  color: var(--neon-color);
}

.layout-type-i .box-body {
  font-size: 26px;
  font-weight: 400;
  line-height: 1.65;
  color: var(--text-on-dark-muted);
}
```

---

### Type J — 상하 반분할형 (실사버전)

> [MVP 제외 — 프로덕트 단계]

**사용 슬롯**: Card 2–4 (에틸렌 실사 시리즈)
**관찰 샘플**: 에틸렌 3화 Card 2, Card 3

```css
/* 변형 1: 텍스트 상단 + 사진 하단 */
.layout-type-j-text-top {
  display: flex;
  flex-direction: column;
  width: 1080px;
  height: 1080px;
  overflow: hidden;
}

.layout-type-j-text-top .text-zone {
  flex: 0 0 65%;     /* 상단 65% (추정) */
  background: #F5F0E8;
  padding: 80px 60px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.layout-type-j-text-top .photo-zone {
  flex: 0 0 35%;
  overflow: hidden;
}

.layout-type-j-text-top .photo-zone img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 변형 2: 사진 상단 + 텍스트 하단 */
.layout-type-j-photo-top {
  display: flex;
  flex-direction: column;
  width: 1080px;
  height: 1080px;
  overflow: hidden;
}

.layout-type-j-photo-top .photo-zone {
  flex: 0 0 35%;
  overflow: hidden;
}

.layout-type-j-photo-top .text-zone {
  flex: 0 0 65%;
  background: var(--surface-base);
  border-radius: 24px 24px 0 0;
  padding: 48px 60px;
}

/* 번호 리스트 (③ 스타일) */
.layout-type-j-photo-top .numbered-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.layout-type-j-photo-top .numbered-list li {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
  font-size: 26px;
  line-height: 1.55;
}

.layout-type-j-photo-top .num-badge {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #333;
  color: var(--text-on-dark);
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 4px;
}
```

---

### Type K — 기관 브랜드 클로징

> [MVP 구현 대상]

**사용 슬롯**: 마지막 카드 (항상, `ClosingCard`)
**관찰 샘플**: 모든 시리즈 최종 카드

```css
.layout-type-k {
  position: relative;
  width: 1080px;
  height: 1080px;
  background: linear-gradient(
    135deg,
    #0A1628 0%,
    #1A3A6E 50%,
    #0A1628 100%
  );  /* 마무리 카드 배경 (추정) */
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 32px;
  padding: 80px;
}

/* 기술선 장식 — 배경 */
.layout-type-k::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(
      90deg,
      rgba(255,255,255,0.03) 0px,
      rgba(255,255,255,0.03) 1px,
      transparent 1px,
      transparent 80px
    );
  z-index: 0;
}

.layout-type-k .org-logo {
  width: 200px;     /* (추정) */
  z-index: 1;
}

.layout-type-k .brand-slogan {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-on-dark);
  text-align: center;
  z-index: 1;
}

.layout-type-k .cta-text {
  font-size: 26px;
  font-weight: 400;
  color: var(--text-on-dark-muted);
  text-align: center;
  z-index: 1;
}
```

**필수 데이터 필드**: `org_name`, `org_logo_url`, `research_dept`, `cta_text`

---

## 6. 반복 컴포넌트 스펙

### 6-1. 흰색 콘텐츠 카드

```css
.content-card-white {
  background: var(--surface-base);
  border-radius: var(--radius-card);  /* 관찰: 16–24px, 기준값 20px */
  padding: 52px 56px;                 /* 관찰: 40–60px 내외 (추정) */
  box-shadow: var(--shadow-card);
  position: relative;
  overflow: hidden;
}

/* 좌측 테마 컬러 액센트 바 (일부 카드) */
.content-card-white.with-accent-bar::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 8px;
  background: var(--theme-primary);
  border-radius: 20px 0 0 20px;
}
```

### 6-2. 다크 원형 번호 배지

```css
.step-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--theme-primary);
  color: var(--text-on-dark);
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 26px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 다크 테마용 */
.step-circle.dark {
  background: #212529;
  border: 2px solid var(--neon-color);
  color: var(--text-on-dark);
}
```

### 6-3. Pill 배지

```css
/* 라이트 배경 위 배지 */
.badge-light {
  display: inline-flex;
  align-items: center;
  height: 48px;
  padding: 0 32px;
  background: var(--badge-bg-light);
  border: 1.5px solid var(--badge-border-light);
  border-radius: var(--radius-pill);
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  backdrop-filter: blur(8px);
}

/* 다크 배경 위 배지 */
.badge-dark {
  display: inline-flex;
  align-items: center;
  height: 48px;
  padding: 0 32px;
  background: rgba(255, 255, 255, 0.10);
  border: 1.5px solid rgba(255, 255, 255, 0.28);
  border-radius: var(--radius-pill);
  font-size: 22px;
  font-weight: 600;
  color: var(--text-on-dark);
  white-space: nowrap;
}

/* 내용 pill (커버 하단 부제) */
.content-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  padding: 0 32px;
  border: 2px solid rgba(255, 255, 255, 0.60);
  border-radius: var(--radius-pill);
  font-size: 24px;
  font-weight: 600;
  color: var(--text-on-dark);
}

.content-pill::before {
  content: '•';
  margin-right: 4px;
}
```

### 6-4. 섹션 헤더 텍스트 블록

```css
.section-header-block {
  margin-bottom: 32px;
}

.section-header-block .eyebrow {
  font-size: 20px;
  font-weight: 600;
  color: var(--theme-primary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.section-header-block .title {
  font-size: 52px;
  font-weight: 800;
  line-height: 1.2;
  color: var(--text-primary);
}

.section-header-block .underline {
  width: 60px;
  height: 6px;
  background: var(--theme-primary);
  border-radius: 3px;
  margin-top: 16px;
}
```

### 6-5. 기관 로고 배치

```css
/* 커버 하단 고정 */
.org-logo-cover {
  position: absolute;
  bottom: 40px;
  left: 60px;
  height: 40px;       /* (추정) */
  z-index: 20;
}

/* 마무리 카드 중앙 */
.org-logo-outro {
  width: 220px;       /* (추정) */
  margin: 0 auto;
}
```

### 6-6. 포인트 언더라인

```css
/* 강조 텍스트 하단 선 */
.point-underline {
  text-decoration: underline;
  text-decoration-color: var(--theme-primary);
  text-decoration-thickness: 4px;  /* (추정) */
  text-underline-offset: 6px;
}

/* 별도 div 언더라인 */
.heading-underline {
  display: block;
  width: 80px;
  height: 5px;
  background: var(--theme-primary);
  border-radius: 3px;
  margin-top: 12px;
}
```

### 6-7. 삼각형 코너 포인트 (커버)

```css
.triangle-corner {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 520px;       /* (추정) */
  height: 520px;
  background: var(--theme-primary);
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
  z-index: 5;
}

/* 아이콘 컨테이너 (삼각형 내부) */
.triangle-icon-wrap {
  position: absolute;
  bottom: 64px;
  right: 64px;
  width: 220px;
  height: 220px;
  z-index: 6;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

### 6-8. 기하도형 오버레이 (마름모)

```css
/* 배경 장식 마름모 (일부 WIT_V2 카드) */
.diamond-decoration {
  position: absolute;
  width: 200px;       /* (추정) */
  height: 200px;
  border: 3px solid rgba(255, 255, 255, 0.15);
  transform: rotate(45deg);
  border-radius: 8px;
  pointer-events: none;
  z-index: 1;
}

.diamond-decoration.top-right {
  top: -80px;
  right: -80px;
  opacity: 0.4;
}

.diamond-decoration.bottom-left {
  bottom: 60px;
  left: 60px;
  width: 120px;
  height: 120px;
  opacity: 0.2;
}
```

---

## 7. 모션/인터랙션 (에디터 미리보기용)

### 7-1. 카드 전환 애니메이션

```css
.card-transition-enter {
  opacity: 0;
  transform: translateX(40px);
  transition: opacity 240ms ease, transform 240ms ease;
}

.card-transition-enter-active {
  opacity: 1;
  transform: translateX(0);
}

.card-transition-exit {
  opacity: 1;
  transform: translateX(0);
  transition: opacity 200ms ease, transform 200ms ease;
}

.card-transition-exit-active {
  opacity: 0;
  transform: translateX(-40px);
}
```

### 7-2. 자동저장 피드백

```css
.autosave-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 20px;
  background: #212529;
  color: var(--text-on-dark);
  border-radius: 8px;
  font-size: 14px;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 200ms ease, transform 200ms ease;
}

.autosave-toast.visible {
  opacity: 1;
  transform: translateY(0);
}
/* 5초 후 자동 소멸: transition-delay 등으로 처리 */
```

### 7-3. 로딩 상태

```css
.card-skeleton {
  width: 1080px;
  height: 1080px;
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 12px;
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* CRITICAL 필드 하이라이트 (ActionBar 잠금 상태) */
.field-critical {
  outline: 2.5px solid #dc3545;
  outline-offset: 2px;
  border-radius: 4px;
}
```

---

## 8. 카드 슬롯 → 카드 타입 매핑 테이블

카드 타입(Pydantic 모델)이 레이아웃을 결정한다. 슬롯별 기본 할당:

| 카드 슬롯 | Pydantic 모델 | 렌더링 레이아웃 | 대안 | 필수 필드 | 선택 필드 |
|-----------|--------------|----------------|------|-----------|-----------|
| Card 1 | `CoverCard` | Type A (고정) | — | `episode_badge`, `main_title_line1`, `main_title_line2`, `theme_primary` | `bg_photo`, `icon_image`, `sub_pill_text` |
| Card 2 | `HookCard` or `TextCard` | Type E (훅 강하면) / Type B (기본) | — | `hook_text` or `section_title` | `bg_photo`, `sub_text`, `accent_keyword` |
| Card 3 | `StatGridCard` or `TextCard` | Type C (수치 3개+) / Type B | — | `section_title`, `stats[]` or `body_text` | `numbered_list[]`, `note_text` |
| Card 4 | `TextCard` or `CompareCard` or `SpecCard` | Type B / Type D / Type F | — | 모델에 따라 다름 | `product_photo`, `compare_left`, `compare_right` |
| Card 5 | `ClosingCard` | Type K (고정) | — | `org_name`, `org_logo_url`, `research_dept`, `cta_text` | — |

> **주의**: 에피소드마다 카드 수가 다름 (5~11장). 파이프라인 기본은 5장.
> Card 3~4는 S6가 논문 내용에 따라 모델 타입을 결정한다.

---

## 9. 주제별 색상 제안 (스마트 기본값)

### 9-1. S6 → S7 색상 주입 흐름

```
1. S6가 논문 주제 분류 → topic_category 결정
2. TOPIC_COLOR_SUGGESTIONS에서 제안 색상 조회
3. S6 JSON theme.primary에 제안 색상 포함
4. 에디터에서 사용자가 색상 피커로 오버라이드 가능
5. default(None)인 경우 사용자 기관 accent color 사용
```

### 9-2. TOPIC_COLOR_SUGGESTIONS

"강제 적용"이 아닌 S6의 제안값. 에디터에서 사용자가 오버라이드 가능.

```python
TOPIC_COLOR_SUGGESTIONS = {
    "agriculture":   "#3BAF6B",   # 농업/식품
    "environment":   "#0EA5BE",   # 환경/기후
    "robotics":      "#F59E20",   # 로봇/기계
    "medical":       "#6C5CE7",   # 의료/바이오
    "materials":     "#7B5FFF",   # 소재/우주
    "chemistry":     "#00C9A7",   # 화학/친환경
    "sensor":        "#F5C430",   # 센서/신선도
    "default":       None,        # → 사용자 org accent color로 fallback
}
```

### 9-3. 테마 적용 위치 (모든 --theme-primary 사용처)

```
1. 삼각형 코너 포인트         → var(--theme-primary) 100%
2. 수치/강조 텍스트            → var(--theme-primary) 100%
3. 섹션 언더라인               → var(--theme-primary) 100%
4. 단계 번호 원형              → var(--theme-primary) 100%
5. 콘텐츠 카드 액센트 바        → var(--theme-primary) 100%
6. 다크 박스 네온 테두리        → var(--neon-color) 80% + glow [MVP 제외 레이아웃]
7. 배지/pill 텍스트 강조        → var(--theme-primary) 100%
```

---

## 10. 샘플 분석 근거 표

| 관찰 항목 | 값 | 추정 여부 | 출처 샘플 |
|-----------|---|-----------|-----------|
| 캔버스 크기 | 1080 × 1080 px | 확인 | HTML `originalWidth/Height` 속성 전체 |
| 시리즈 배지 형태 | pill (border-radius: 100px) | 확인 | 13화 Card 1, 16화 Card 1, 3화 Card 1 |
| WIT_V2 커버 삼각형 위치 | bottom-right 코너 | 확인 | 13화·15화·16화 Card 1 |
| WIT_V2 커버 삼각형 크기 | ~520×520px | 추정 | 13화 Card 1 시각 추산 |
| 커버 배지 위치 | top-center, y≈72px | 추정 | 13화·15화·16화 Card 1 |
| 흰색 카드 border-radius | 20px | 추정 | 16화 Card 3~5, 13화 Card 2~4 |
| 흰색 카드 padding | 52px 56px | 추정 | 16화·13화 본문 카드 |
| 외부 여백 (safe zone) | 60px | 추정 | 전체 샘플 콘텐츠 배치 관찰 |
| D1 폰트 사이즈 (커버 대타이틀) | 100–120px | 추정 | 에틸렌 3화 Card 1 ("에틸렌"=노랑 대형) |
| H1 폰트 사이즈 | 52–64px | 추정 | 13화·16화 본문 카드 제목 |
| B1 폰트 사이즈 | 24–28px | 추정 | HTML 본문 텍스트 크기 기준 |
| 단계 번호 원형 크기 | 64px | 추정 | 혈당 센서 ①②③ 카드 관찰 |
| 13화 테마 컬러 | 녹색 계열 (#3BAF6B 부근) | 추정 | 13화 Card 1 삼각형 |
| 15화 테마 컬러 | 청록 계열 (#0EA5BE 부근) | 추정 | 15화 Card 1 삼각형 |
| 16화 테마 컬러 | 앰버 계열 (#F59E20 부근) | 추정 | 16화 Card 1 |
| 다크 배경색 | #080C18 부근 | 추정 | HMF·3D 커버 관찰 |
| HMF 네온 컬러 | 민트 (#00FFC8 부근) | 추정 | HMF 9화 Card 2~6 박스 테두리 |
| 3D 네온 컬러 | 보라 (#7B5FFF 부근) | 추정 | 3D 4화 Card 2~7 박스 테두리 |
| 에틸렌 노랑 강조 | #F5C430 부근 | 추정 | 에틸렌 3화 Card 1 "에틸렌" 텍스트 |
| 마무리 카드 배경 | 다크 그라디언트 (#0A1628~#1A3A6E) | 추정 | 전체 시리즈 최종 카드 |
| 상하 분할 비율 (사진:텍스트) | 35:65 | 추정 | 에틸렌 3화 Card 2, 3 |
| WIT_V2 폰트 계열 | Pretendard / Noto Sans KR | 추정 | 전체 WIT_V2 샘플 |
| box-shadow (흰 카드) | 4px 16px + 16px 48px | 추정 | 스타일 추론 |

---

## 11. 샘플 분석 한계 및 추가 확인 필요 사항

### 11-1. 고해상도 원본 미확보

네이버 블로그 저장 파일 특성상 카드 4~9번(에틸렌 3화), 4~6번(기타) 등 **일부 카드가 썸네일 해상도(~100×100px)** 로만 저장되었다.
해당 카드들의 레이아웃은 HTML 텍스트로 내용만 확인하였으며, 시각 구조는 추정이다.

**필요 조치**: 실제 1080px 원본 이미지로 재측정 권장 (네이버 블로그 원문 접근 또는 Figma 원본 파일).

### 11-2. 정확한 hex 값 미측정

모든 색상은 시각적 관찰(색조 판단)로 추정. 실제 구현 전:
- Chrome DevTools의 color picker로 원본 이미지 픽셀 추출
- 또는 Figma 파일 접근 후 정확한 토큰 확인

### 11-3. 미분석 샘플

| 샘플 | 경로 | 상태 |
|------|------|------|
| What if Technology 2화 | `[What if Technology 2화] 만.. _ 네이버블로그_files/` | 미분석 |
| 생기원 기술 이야기 6화 | glob에서 참조 발견 | 미분석 |
| 생기원 기술 이야기 2화 | glob에서 참조 발견 | 미분석 |

### 11-4. 폰트 라이선스 확인 필요

Pretendard (SIL OFL) vs Noto Sans KR (Apache 2.0) — 모두 상업적 무료. 단, 원본 KITECH 실제 사용 폰트가 별도 구매 폰트일 가능성 있음 (상기 두 폰트는 웹폰트 대체안).

### 11-5. 반응형/모바일 버전

현재 스펙은 1080×1080px 출력 전용. 에디터 UI의 미리보기 축소 비율(예: 540px display)은 CSS `transform: scale(0.5)`으로 처리 권장.

### 11-6. 이미지 슬롯 구체적 크기

Type F(스펙형) 및 Type J(반분할)의 사진 크기/비율은 콘텐츠에 따라 가변. S7 구현 시 `object-fit: cover` + 고정 영역으로 처리하되, 사진 없을 경우 fallback 색상 처리 필요.

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2026-05-11 | 초기 작성 (KITECH 샘플 분석 기반) |
| v2.0 | 2026-05-11 | PolyInsight 독자 디자인 시스템으로 재정의. 색상 토큰 2계층 구조 전환, 역할 기반 토큰명 통일, Type H·I·J MVP 제외 표기, Type K 기관 브랜드 클로징으로 재정의, 카드 매핑 Pydantic 모델 기반으로 교체, TOPIC_COLOR_SUGGESTIONS 도입 |

*끝. 수치 재측정 후 `(추정)` 항목을 순차 확정하여 버전 업.*
