# 배경색 변경 + ColorPicker 컴포넌트 설계
> 2026-06-04 | 브레인스토밍 확정본

---

## Problem

현재 모든 카드 템플릿이 배경색을 파일마다 하드코딩하고 있어 (`#111`, `#0A0F1E` 등) 코드 변경 없이는 배경색을 바꿀 수 없다. 사용자(박사님)가 black 고정 배경을 다양하게 변경하고 싶다는 요구가 있었다.

## Decision

1. **`CardEditorData.bg_color`** 필드를 추가해 전체 카드 배경색을 전역 관리
2. **재사용 가능한 `ColorPicker` 컴포넌트** 를 신규 제작 — 배경색뿐 아니라 테마·그래프색 등 어디든 재사용
3. **RightPanel "색상" 아코디언 섹션** — 기존 "테마 색상" 섹션을 통합 색상 섹션으로 교체
4. **`--theme-bg` CSS 변수** — CardFrame이 주입, 12개 템플릿이 참조

## Scope

- 배경색 적용 단위: **전체 카드 일괄 (Global)** — 카드마다 개별 배경색 지원 안 함
- 테마(primary/dark)와 배경색은 **독립 컨트롤**
- 이번 작업에서 추가되는 CSS 변수: `--theme-bg` 하나만

---

## Architecture

### 데이터 모델

**백엔드 (`backend/core/models.py`)**
```python
class CardEditorData(BaseModel):
    storyboard: Storyboard | None = None
    meta: CardMeta
    cards: List[CardSlot]
    theme: CardTheme = Field(default_factory=CardTheme)
    recommended_theme_key: str | None = None
    bg_color: str = "#111111"   # 신규
```

**프론트엔드 (`web/src/types/editor.ts`)**
```ts
interface CardEditorData {
  // 기존 필드...
  bg_color?: string   // 기본값 "#111111"
}
```

S6는 bg_color를 생성하지 않으므로 항상 기본값으로 시작. 사용자가 에디터에서 변경 → 기존 auto-save(5초 idle) 경로로 PATCH.

---

### ColorPicker 컴포넌트

**파일:** `web/src/components/ui/ColorPicker.tsx`

```tsx
interface ColorPickerProps {
  value: string                    // 현재 색상 (hex)
  onChange: (hex: string) => void
  presets?: string[]               // 없으면 기본 8개 사용
}
```

**기본 프리셋 8개:**
```
#111111  #0A0F1E  #0D1F12  #1A0A2E
#1C1008  #1A1A1A  #F5F0E8  #FFFFFF
```

**내부 상태:**
- `open: boolean` — 스펙트럼 영역 펼침/닫힘
- `hue: number` — 색조 슬라이더 (0~360)
- `hex: string` — 입력 중인 hex 문자열 (확정 전 로컬 상태)

**렌더 구조:**
```
┌─ 프리셋 스와치 행 ─────────── [+토글] ─┐
│  ● ● ● ● ● ● ● ●                    │
├─ hex 인풋 ──────────────────────────┤
│  [■현재색] [#111111__________]       │
├─ (open) 스펙트럼 ───────────────────┤
│  [색조×명도 그라디언트 — 드래그 핸들]   │
│  [══════ 색조 슬라이더 (무지개) ═════] │
│  R[17] G[17] B[17]  HEX[#111111]    │
└──────────────────────────────────────┘
```

**동작 규칙:**
- 프리셋 클릭 → 즉시 `onChange` 호출
- `+` 클릭 → 스펙트럼 토글
- hex 입력 → 유효한 6자리(#포함 7자)일 때만 `onChange`
- RGB 입력 → 실시간 hex 변환 후 `onChange`
- 스펙트럼 드래그 → mousedown + mousemove로 핸들 위치 추적 → `onChange`

**재사용처 (미래):**
- 테마 primary/dark 커스텀 색상
- 데이터 차트 바 색상
- 텍스트 강조색 (rich text 서식툴바)

---

### RightPanel 재구조화

**파일:** `web/src/components/editor/RightPanel.tsx`

기존 "테마 색상" 섹션(프리셋 스와치 6개) → 통합 "색상" 아코디언 섹션으로 교체.

**섹션 구조:**
```
§1 — 색상 (아코디언)
  ┌─ 배경      [■ #111111 ▾] ──────────────────┐
  │   행 클릭 → ColorPicker 인라인 펼침          │
  ├─ 테마 강조  [■ #2563EB ▾] ── [AI] 배지      │
  │   행 클릭 → ColorPicker 펼침                │
  │   presets = 기존 THEME_PRESETS 6개 색상     │
  └─ (미래 확장) 그래프 바, 텍스트 강조 행 추가  │
─────────────────────────────────────────────
§2 — 이미지     (기존 그대로)
§3 — 타이포그래피 (기존 그대로)
```

**Props 변경:**
```tsx
// 신규
bgColor: string
onBgColorChange: (hex: string) => void
// 기존 유지
onThemeChange: (theme: CardTheme) => void
currentThemePrimary?: string
recommendedThemeKey?: string
```

AI 추천 배지: "테마 강조" 행 옆에 `[AI]` 칩으로 유지.

---

### CardFrame + 템플릿

**파일:** `web/src/components/cards/CardFrame.tsx`

```tsx
interface CardFrameProps {
  theme: CardTheme
  bgColor?: string       // 신규
  scale?: number
  children: ReactNode
  className?: string
}

// innerStyle에 추가:
'--theme-bg': bgColor ?? '#111111',
// 기존 background: '#FFFFFF' 제거 (--theme-bg로 대체)
```

CardFrame이 주입하는 CSS 변수 전체:
```
--theme-primary  (기존)
--theme-dark     (기존)
--theme-bg       (신규)
```

**템플릿 12개 일괄 변경:**

각 템플릿의 루트 `<div>` 배경색 한 줄만 교체.

```tsx
// 변경 전
<div style={{ background: '#111', ... }}>

// 변경 후
<div style={{ background: 'var(--theme-bg, #111111)', ... }}>
```

대상: `CoverCard`, `HookCard`, `ProblemCard`, `Circle3Card`, `Compare2Card`,
`Grid4Card`, `DefinitionCard`, `FlowCard`, `DataCard`, `ShowcaseCard`,
`ClosingCard`, `BrandCard`

**에디터 페이지 데이터 흐름:**
```
cardData.bg_color
  → editor/[jobId]/page.tsx (state)
  → MidCanvas → CardRenderer → CardFrame (bgColor prop)
  → --theme-bg CSS 변수
  → 12개 템플릿 참조
```

---

### S7 렌더링

**파일:** `web/src/app/render/[jobId]/[cardNum]/page.tsx`

변경 범위: 이 파일 하나만.

```
DB에서 cardData 읽기 (bg_color 포함)
  → CardFrame에 bgColor={cardData.bg_color ?? '#111111'} 추가
  → --theme-bg 적용된 카드 렌더
  → Playwright 스크린샷 → PNG에 배경색 반영
```

`s7_renderer.py` 변경 없음 — bg_color가 DB에 저장되어 있으면 자동으로 렌더 라우트에 반영됨.

---

## Rationale

- **전역 적용**: 독자 피드백 "카드 2·3이 다른 카드뉴스인 줄 알았다" — 시각 일관성 보장
- **테마와 독립**: primary/dark(강조색)와 background는 서로 다른 디자인 결정. 묶으면 유연성 저하
- **CSS 변수 하나**: `--theme-bg` 추가만으로 12개 템플릿에 일괄 적용 — 최소 변경, 최대 효과
- **ColorPicker 재사용**: 한 번 만들어두면 테마·그래프·텍스트 강조 등 어디든 `<ColorPicker value onChange />` 한 줄로 사용

## Risks

- **라이트 배경 가독성**: 흰색/아이보리 배경 선택 시 흰 텍스트가 안 보임. 현재 설계에서는 프리셋에 라이트 색상도 포함하되, 텍스트 자동 반전 로직은 이번 스코프 밖. 사용자 책임.
- **스펙트럼 드래그 구현 복잡도**: mousedown/mousemove/mouseup + touch 이벤트 처리. 라이브러리(`react-colorful` 등) 활용 고려 가능 — 구현 단계에서 결정.
