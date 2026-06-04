# Background Color + ColorPicker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전체 카드 배경색을 RightPanel에서 자유롭게 변경할 수 있는 ColorPicker를 만들고, 테마 강조색과 독립된 색상 아코디언 섹션으로 통합한다.

**Architecture:** `CardEditorData.bg_color` (전역 배경색 필드) → `CardFrame`이 `--theme-bg` CSS 변수로 주입 → 12개 템플릿이 참조. 재사용 가능한 `ColorPicker` 컴포넌트를 신규 제작해 RightPanel의 통합 색상 섹션에 배치.

**Tech Stack:** Next.js 15, TypeScript, React hooks, FastAPI/Pydantic, CSS custom properties

---

## File Map

| 상태 | 파일 | 변경 내용 |
|------|------|-----------|
| 수정 | `backend/core/models.py` | `CardEditorData.bg_color` 필드 추가 |
| 수정 | `web/src/types/editor.ts` | `CardDataPayload.bg_color` 필드 추가 |
| 수정 | `web/src/components/cards/CardFrame.tsx` | `bgColor` prop + `--theme-bg` 주입 |
| 수정 | `web/src/components/cards/CardRenderer.tsx` | `bgColor` prop → CardFrame 전달 |
| 수정 | `web/src/components/cards/templates/*.tsx` (12개) | 루트 background → `var(--theme-bg, #111111)` |
| 신규 | `web/src/components/ui/ColorPicker.tsx` | 재사용 가능한 컬러피커 컴포넌트 |
| 수정 | `web/src/components/editor/RightPanel.tsx` | 통합 색상 아코디언 섹션 |
| 수정 | `web/src/components/editor/MidCanvas.tsx` | `bgColor` prop 추가 + CardRenderer 전달 |
| 수정 | `web/src/app/editor/[jobId]/page.tsx` | `handleBgColorChange` + RightPanel/MidCanvas 배선 |
| 수정 | `web/src/app/render/[jobId]/[cardNum]/page.tsx` | `bgColor` CardRenderer 전달 |

---

## Task 1: 백엔드 모델에 bg_color 추가

**Files:**
- Modify: `backend/core/models.py:113-118`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 테스트 작성**

`backend/tests/test_api.py` 끝에 추가:

```python
def test_card_editor_data_bg_color_default():
    from backend.core.models import CardEditorData, CardMeta, FieldValue, FieldSource, MatchQuality, ClaimType, RiskLevel
    fv = FieldValue(
        value="test", confidence="high",
        match_quality=MatchQuality.EXACT, claim_type=ClaimType.QUALITATIVE,
        source=FieldSource(section="test", page=1), risk_level=RiskLevel.LOW,
    )
    meta = CardMeta(
        org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv,
    )
    data = CardEditorData(meta=meta, cards=[])
    assert data.bg_color == "#111111"

def test_card_editor_data_bg_color_custom():
    from backend.core.models import CardEditorData, CardMeta, FieldValue, FieldSource, MatchQuality, ClaimType, RiskLevel
    fv = FieldValue(
        value="test", confidence="high",
        match_quality=MatchQuality.EXACT, claim_type=ClaimType.QUALITATIVE,
        source=FieldSource(section="test", page=1), risk_level=RiskLevel.LOW,
    )
    meta = CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv)
    data = CardEditorData(meta=meta, cards=[], bg_color="#0A0F1E")
    assert data.bg_color == "#0A0F1E"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && python -m pytest tests/test_api.py::test_card_editor_data_bg_color_default -v
```
Expected: `AttributeError` 또는 `FAILED`

- [ ] **Step 3: 모델 수정**

`backend/core/models.py` — `CardEditorData` 클래스:

```python
class CardEditorData(BaseModel):
    storyboard: Storyboard | None = None
    meta: CardMeta
    cards: List[CardSlot]
    theme: CardTheme = Field(default_factory=CardTheme)
    recommended_theme_key: str | None = None
    bg_color: str = "#111111"   # 전체 카드 배경색 (테마와 독립)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && python -m pytest tests/test_api.py::test_card_editor_data_bg_color_default tests/test_api.py::test_card_editor_data_bg_color_custom -v
```
Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/core/models.py backend/tests/test_api.py
git commit -m "[BE] CardEditorData에 bg_color 필드 추가 (기본값 #111111)"
```

---

## Task 2: 프론트엔드 타입에 bg_color 추가

**Files:**
- Modify: `web/src/types/editor.ts`

- [ ] **Step 1: `CardDataPayload` 인터페이스 수정**

`web/src/types/editor.ts`:

```typescript
export interface CardDataPayload {
  cards: Card[]
  theme?: CardTheme
  recommended_theme_key?: string
  bg_color?: string   // 전체 카드 배경색 (기본값 #111111)
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음 (bg_color는 optional이라 기존 코드 영향 없음)

- [ ] **Step 3: 커밋**

```bash
git add web/src/types/editor.ts
git commit -m "[WEB] CardDataPayload에 bg_color 타입 추가"
```

---

## Task 3: CardFrame + CardRenderer에 bgColor 배선

**Files:**
- Modify: `web/src/components/cards/CardFrame.tsx`
- Modify: `web/src/components/cards/CardRenderer.tsx`

- [ ] **Step 1: CardFrame 수정**

`web/src/components/cards/CardFrame.tsx` 전체 교체:

```tsx
'use client'

import { type CSSProperties, type ReactNode } from 'react'
import type { CardTheme } from '@/types/editor'
import styles from './cards.module.css'

const CARD_SIZE = 1080

interface CardFrameProps {
  theme: CardTheme
  bgColor?: string
  scale?: number
  children: ReactNode
  className?: string
}

export default function CardFrame({ theme, bgColor = '#111111', scale = 1, children, className }: CardFrameProps) {
  const wrapperStyle: CSSProperties = {
    width: CARD_SIZE * scale,
    height: CARD_SIZE * scale,
    position: 'relative',
    overflow: 'hidden',
  }

  const innerStyle: CSSProperties = {
    '--theme-primary': theme.primary,
    '--theme-dark': theme.dark,
    '--theme-bg': bgColor,
    width: CARD_SIZE,
    height: CARD_SIZE,
    position: 'relative',
    overflow: 'hidden',
    background: 'var(--theme-bg)',
    fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    boxSizing: 'border-box',
    ...(scale === 1
      ? {}
      : { transform: `scale(${scale})`, transformOrigin: 'top left' }),
  } as CSSProperties

  return (
    <div style={wrapperStyle} className={className}>
      <div className={styles.scope} style={innerStyle}>
        {children}
      </div>
    </div>
  )
}

export { styles as cardStyles }
```

- [ ] **Step 2: CardRenderer 수정**

`web/src/components/cards/CardRenderer.tsx`:

```tsx
'use client'

import CardFrame from './CardFrame'
import { CARD_COMPONENTS } from './index'
import type { CardComponentProps } from './types'

interface CardRendererProps extends CardComponentProps {
  scale?: number
  bgColor?: string
}

export default function CardRenderer({ scale = 1, bgColor, ...props }: CardRendererProps) {
  const { card, theme } = props
  const Component = CARD_COMPONENTS[card.template_type]

  return (
    <CardFrame theme={theme} bgColor={bgColor} scale={scale}>
      {Component ? <Component {...props} /> : <UnimplementedTemplate templateType={card.template_type} />}
    </CardFrame>
  )
}

function UnimplementedTemplate({ templateType }: { templateType: string }) {
  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--theme-bg, #111111)',
      color: '#666', fontFamily: 'Noto Sans KR, sans-serif', gap: 16,
    }}>
      <div style={{ fontSize: 80 }}>🚧</div>
      <div style={{ fontSize: 40, fontWeight: 700 }}>{templateType}</div>
      <div style={{ fontSize: 22, color: '#999' }}>Phase 2에서 구현 예정</div>
    </div>
  )
}
```

- [ ] **Step 3: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/cards/CardFrame.tsx web/src/components/cards/CardRenderer.tsx
git commit -m "[WEB] CardFrame --theme-bg CSS 변수 주입, CardRenderer bgColor prop 추가"
```

---

## Task 4: 템플릿 12개 배경색 CSS 변수 적용

**Files:**
- Modify: `web/src/components/cards/templates/` 하위 12개 파일

각 파일의 루트 `<div>` background 값을 `var(--theme-bg, #111111)` 으로 교체한다.

- [ ] **Step 1: CoverCard**

`web/src/components/cards/templates/CoverCard.tsx` 21번째 줄:
```tsx
// 변경 전
<div style={{ width: '100%', height: '100%', background: '#0A0F1E', position: 'relative' }}>
// 변경 후
<div style={{ width: '100%', height: '100%', background: 'var(--theme-bg, #111111)', position: 'relative' }}>
```

- [ ] **Step 2: HookCard**

`web/src/components/cards/templates/HookCard.tsx` 21번째 줄:
```tsx
// 변경 전
<div style={{ width: '100%', height: '100%', background: '#111', position: 'relative' }}>
// 변경 후
<div style={{ width: '100%', height: '100%', background: 'var(--theme-bg, #111111)', position: 'relative' }}>
```

- [ ] **Step 3: 나머지 10개 템플릿**

아래 각 파일의 루트 `<div>` background 를 동일하게 `var(--theme-bg, #111111)` 으로 교체:
- `ProblemCard.tsx`
- `Circle3Card.tsx`
- `Compare2Card.tsx`
- `Grid4Card.tsx`
- `DefinitionCard.tsx`
- `FlowCard.tsx`
- `DataCard.tsx`
- `ShowcaseCard.tsx`
- `ClosingCard.tsx`
- `BrandCard.tsx`

각 파일에서 루트 div의 `background:` 값을 찾아 `var(--theme-bg, #111111)` 으로 교체한다. 루트 div는 `style={{ width: '100%', height: '100%', ...` 형태의 첫 번째 div다.

- [ ] **Step 4: 타입 체크 + 빌드 확인**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음

- [ ] **Step 5: 커밋**

```bash
git add web/src/components/cards/templates/
git commit -m "[WEB] 템플릿 12개 배경색 var(--theme-bg) 적용"
```

---

## Task 5: ColorPicker 컴포넌트 구현

**Files:**
- Create: `web/src/components/ui/ColorPicker.tsx`

- [ ] **Step 1: 색상 변환 유틸리티 작성**

`web/src/components/ui/ColorPicker.tsx` 생성:

```tsx
'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

// ── 색상 변환 유틸 ──────────────────────────────────────────────────────────

export function hexToHsv(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const d = max - min
  let h = 0
  if (d !== 0) {
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6
    else if (max === g) h = ((b - r) / d + 2) / 6
    else h = ((r - g) / d + 4) / 6
  }
  return [h * 360, max === 0 ? 0 : d / max, max]
}

export function hsvToHex(h: number, s: number, v: number): string {
  const f = (n: number) => {
    const k = (n + h / 60) % 6
    return v - v * s * Math.max(0, Math.min(k, 4 - k, 1))
  }
  const toHex = (x: number) => Math.round(x * 255).toString(16).padStart(2, '0')
  return `#${toHex(f(5))}${toHex(f(3))}${toHex(f(1))}`
}

function isValidHex(s: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(s)
}

function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  const hex = hsvToHex(h, s, v)
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
}

// ── 기본 프리셋 ─────────────────────────────────────────────────────────────

const DEFAULT_PRESETS = [
  '#111111', '#0A0F1E', '#0D1F12', '#1A0A2E',
  '#1C1008', '#1A1A1A', '#F5F0E8', '#FFFFFF',
]

// ── Props ───────────────────────────────────────────────────────────────────

interface ColorPickerProps {
  value: string
  onChange: (hex: string) => void
  presets?: string[]
}

// ── 컴포넌트 ────────────────────────────────────────────────────────────────

export default function ColorPicker({ value, onChange, presets = DEFAULT_PRESETS }: ColorPickerProps) {
  const safeValue = isValidHex(value) ? value : '#111111'
  const [hsv, setHsv] = useState<[number, number, number]>(() => hexToHsv(safeValue))
  const [open, setOpen] = useState(false)
  const [hexInput, setHexInput] = useState(safeValue)
  const [rgb, setRgb] = useState<[number, number, number]>(() => hsvToRgb(...hexToHsv(safeValue)))

  const spectrumRef = useRef<HTMLDivElement>(null)
  const hueRef = useRef<HTMLDivElement>(null)
  const draggingSpectrum = useRef(false)
  const draggingHue = useRef(false)

  // 외부 value 변경 동기화
  useEffect(() => {
    if (!isValidHex(value)) return
    const newHsv = hexToHsv(value)
    setHsv(newHsv)
    setHexInput(value)
    setRgb(hsvToRgb(...newHsv))
  }, [value])

  const commit = useCallback((newHsv: [number, number, number]) => {
    const hex = hsvToHex(...newHsv)
    setHsv(newHsv)
    setHexInput(hex)
    setRgb(hsvToRgb(...newHsv))
    onChange(hex)
  }, [onChange])

  // 스펙트럼 드래그
  const handleSpectrumPointer = useCallback((e: React.PointerEvent) => {
    const el = spectrumRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const s = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const v = Math.max(0, Math.min(1, 1 - (e.clientY - rect.top) / rect.height))
    commit([hsv[0], s, v])
  }, [hsv, commit])

  // 색조 슬라이더
  const handleHuePointer = useCallback((e: React.PointerEvent) => {
    const el = hueRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const h = Math.max(0, Math.min(360, ((e.clientX - rect.left) / rect.width) * 360))
    commit([h, hsv[1], hsv[2]])
  }, [hsv, commit])

  const currentHex = hsvToHex(...hsv)

  return (
    <div style={{ userSelect: 'none' }}>
      {/* 프리셋 스와치 행 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {presets.map((p) => (
          <button
            key={p}
            onClick={() => { commit(hexToHsv(p)); onChange(p) }}
            style={{
              width: 24, height: 24, borderRadius: '50%', background: p, border: 'none',
              cursor: 'pointer', flexShrink: 0,
              outline: currentHex.toLowerCase() === p.toLowerCase() ? '2px solid var(--brand, #16A34A)' : '1px solid rgba(255,255,255,0.2)',
              outlineOffset: 2,
            }}
            aria-label={p}
          />
        ))}
        {/* 피커 토글 */}
        <button
          onClick={() => setOpen((v) => !v)}
          style={{
            width: 24, height: 24, borderRadius: '50%', background: 'transparent',
            border: '1.5px dashed rgba(255,255,255,0.3)', cursor: 'pointer',
            color: 'rgba(255,255,255,0.5)', fontSize: 14, lineHeight: 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          aria-label="색상 피커 열기"
        >
          {open ? '×' : '+'}
        </button>
      </div>

      {/* Hex 인풋 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: open ? 10 : 0 }}>
        <div style={{ width: 24, height: 24, borderRadius: 4, background: currentHex, border: '1px solid rgba(255,255,255,0.2)', flexShrink: 0 }} />
        <input
          value={hexInput}
          onChange={(e) => {
            const v = e.target.value
            setHexInput(v)
            if (isValidHex(v)) commit(hexToHsv(v))
          }}
          style={{
            flex: 1, background: 'var(--canvas-subtle, #1a1a1a)',
            border: '1px solid var(--border-subtle, #333)',
            borderRadius: 6, padding: '4px 8px',
            fontSize: 12, color: 'var(--ink, #fff)', fontFamily: 'monospace',
          }}
          spellCheck={false}
        />
      </div>

      {/* 스펙트럼 + 슬라이더 (open일 때만) */}
      {open && (
        <div style={{ marginTop: 8, borderRadius: 8, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
          {/* 색조×명도 스펙트럼 */}
          <div
            ref={spectrumRef}
            style={{
              height: 120,
              background: `
                linear-gradient(to bottom, transparent, #000),
                linear-gradient(to right, #fff, hsl(${hsv[0]}, 100%, 50%))
              `,
              position: 'relative', cursor: 'crosshair',
            }}
            onPointerDown={(e) => { draggingSpectrum.current = true; e.currentTarget.setPointerCapture(e.pointerId); handleSpectrumPointer(e) }}
            onPointerMove={(e) => { if (draggingSpectrum.current) handleSpectrumPointer(e) }}
            onPointerUp={() => { draggingSpectrum.current = false }}
          >
            {/* 핸들 */}
            <div style={{
              position: 'absolute',
              left: `${hsv[1] * 100}%`,
              top: `${(1 - hsv[2]) * 100}%`,
              width: 10, height: 10, borderRadius: '50%',
              border: '2px solid #fff', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none',
            }} />
          </div>

          {/* 색조 슬라이더 */}
          <div
            ref={hueRef}
            style={{
              height: 12, margin: '8px 10px 4px',
              background: 'linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)',
              borderRadius: 6, cursor: 'pointer', position: 'relative',
            }}
            onPointerDown={(e) => { draggingHue.current = true; e.currentTarget.setPointerCapture(e.pointerId); handleHuePointer(e) }}
            onPointerMove={(e) => { if (draggingHue.current) handleHuePointer(e) }}
            onPointerUp={() => { draggingHue.current = false }}
          >
            <div style={{
              position: 'absolute', top: '50%', left: `${(hsv[0] / 360) * 100}%`,
              width: 12, height: 12, borderRadius: '50%',
              background: `hsl(${hsv[0]}, 100%, 50%)`,
              border: '2px solid #fff', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none',
            }} />
          </div>

          {/* RGB + HEX 직접 입력 */}
          <div style={{ display: 'flex', gap: 4, padding: '4px 10px 10px', fontSize: 10 }}>
            {(['R', 'G', 'B'] as const).map((ch, i) => (
              <div key={ch} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{ch}</div>
                <input
                  type="number" min={0} max={255}
                  value={rgb[i]}
                  onChange={(e) => {
                    const newRgb: [number, number, number] = [...rgb] as [number, number, number]
                    newRgb[i] = Math.max(0, Math.min(255, Number(e.target.value)))
                    const hex = `#${newRgb.map((v) => v.toString(16).padStart(2, '0')).join('')}`
                    commit(hexToHsv(hex))
                  }}
                  style={{
                    width: '100%', background: 'var(--canvas-subtle, #1a1a1a)',
                    border: '1px solid var(--border-subtle, #333)', borderRadius: 4,
                    padding: '2px 4px', color: 'var(--ink, #fff)',
                    fontFamily: 'monospace', fontSize: 10, textAlign: 'center',
                  }}
                />
              </div>
            ))}
            <div style={{ flex: 1.5, textAlign: 'center' }}>
              <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>HEX</div>
              <input
                value={hexInput}
                onChange={(e) => {
                  const v = e.target.value
                  setHexInput(v)
                  if (isValidHex(v)) commit(hexToHsv(v))
                }}
                style={{
                  width: '100%', background: 'var(--canvas-subtle, #1a1a1a)',
                  border: '1px solid var(--border-subtle, #333)', borderRadius: 4,
                  padding: '2px 4px', color: 'var(--ink, #fff)',
                  fontFamily: 'monospace', fontSize: 10, textAlign: 'center',
                }}
                spellCheck={false}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/ui/ColorPicker.tsx
git commit -m "[WEB] ColorPicker 재사용 가능 컴포넌트 신규 추가"
```

---

## Task 6: RightPanel — 통합 색상 아코디언

**Files:**
- Modify: `web/src/components/editor/RightPanel.tsx`

- [ ] **Step 1: Props 확장**

`RightPanel.tsx` 상단 `Props` 인터페이스:

```tsx
interface Props {
  jobId: string
  activeCard?: Card
  onImageUpdate: (imageUrl: string | null) => void
  imageUploadRequested?: boolean
  onImageUploadHandled?: () => void
  currentThemePrimary?: string
  recommendedThemeKey?: string
  onThemeChange: (theme: CardTheme) => void
  bgColor: string                              // 신규
  onBgColorChange: (hex: string) => void       // 신규
}
```

- [ ] **Step 2: ColorPicker import + THEME_PRESETS 색상 추출**

파일 상단 import 추가:

```tsx
import ColorPicker from '@/components/ui/ColorPicker'
import { hexToHsv, hsvToHex } from '@/components/ui/ColorPicker'
```

`THEME_PRESETS` 상수 아래에 테마용 프리셋 배열 추가:

```tsx
const THEME_PRIMARY_PRESETS = THEME_PRESETS.map((t) => t.primary)
```

- [ ] **Step 3: 아코디언 상태 추가**

컴포넌트 상단 `useState` 선언부에 추가:

```tsx
const [openColorRow, setOpenColorRow] = useState<'bg' | 'theme' | null>(null)
```

- [ ] **Step 4: §1 — "테마 색상" 섹션을 "색상" 아코디언으로 교체**

기존 `{/* §1 — 테마 색상 */}` 섹션 전체를 아래로 교체:

```tsx
{/* §1 — 색상 (아코디언) */}
<section>
  <SectionHead>색상</SectionHead>
  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
    {/* 배경색 행 */}
    <div>
      <button
        onClick={() => setOpenColorRow((v) => v === 'bg' ? null : 'bg')}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '7px 10px', borderRadius: 8, border: '1px solid transparent',
          background: openColorRow === 'bg' ? 'var(--canvas-subtle)' : 'transparent',
          cursor: 'pointer',
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>배경</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 16, height: 16, borderRadius: 3, background: bgColor, border: '1px solid rgba(255,255,255,0.2)' }} />
          <span style={{ fontSize: 11, color: 'var(--ink-3)', fontFamily: 'monospace' }}>{bgColor}</span>
          <span style={{ fontSize: 10, color: 'var(--ink-3)' }}>{openColorRow === 'bg' ? '▴' : '▾'}</span>
        </div>
      </button>
      {openColorRow === 'bg' && (
        <div style={{ padding: '8px 10px 10px' }}>
          <ColorPicker value={bgColor} onChange={onBgColorChange} />
        </div>
      )}
    </div>

    {/* 테마 강조색 행 */}
    <div>
      <button
        onClick={() => setOpenColorRow((v) => v === 'theme' ? null : 'theme')}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '7px 10px', borderRadius: 8, border: '1px solid transparent',
          background: openColorRow === 'theme' ? 'var(--canvas-subtle)' : 'transparent',
          cursor: 'pointer', position: 'relative',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>테마 강조</span>
          {recommendedThemeKey && (
            <span style={{ fontSize: 8, fontWeight: 700, background: '#16A34A', color: '#fff', padding: '1px 5px', borderRadius: 10 }}>
              AI
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 16, height: 16, borderRadius: 3, background: currentThemePrimary ?? '#2563EB', border: '1px solid rgba(255,255,255,0.2)' }} />
          <span style={{ fontSize: 11, color: 'var(--ink-3)', fontFamily: 'monospace' }}>{currentThemePrimary ?? '#2563EB'}</span>
          <span style={{ fontSize: 10, color: 'var(--ink-3)' }}>{openColorRow === 'theme' ? '▴' : '▾'}</span>
        </div>
      </button>
      {openColorRow === 'theme' && (
        <div style={{ padding: '8px 10px 10px' }}>
          <ColorPicker
            value={currentThemePrimary ?? '#2563EB'}
            onChange={(hex) => {
              // dark = primary를 HSV V값 65%로 어둡게
              const [h, s, v] = hexToHsv(hex)
              const dark = hsvToHex(h, s, v * 0.65)
              onThemeChange({ primary: hex, dark })
            }}
            presets={THEME_PRIMARY_PRESETS}
          />
        </div>
      )}
    </div>
  </div>
</section>
```

- [ ] **Step 5: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: `bgColor` 및 `onBgColorChange` prop 미전달로 에러 발생 (다음 Task에서 해결)

- [ ] **Step 6: 커밋**

```bash
git add web/src/components/editor/RightPanel.tsx web/src/components/ui/ColorPicker.tsx
git commit -m "[WEB] RightPanel 통합 색상 아코디언 + ColorPicker 연결"
```

---

## Task 7: 에디터 페이지 배선

**Files:**
- Modify: `web/src/app/editor/[jobId]/page.tsx`
- Modify: `web/src/components/editor/MidCanvas.tsx`

- [ ] **Step 1: MidCanvas에 bgColor prop 추가**

`web/src/components/editor/MidCanvas.tsx` — Props 인터페이스:

```tsx
interface Props {
  jobId: string
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  theme?: CardTheme
  bgColor?: string           // 신규
  isDemo?: boolean
  focusedField?: string | null
  onFieldFocus?: (field: string) => void
  onFieldChange?: (fieldKey: string, value: string) => void
  onImageUploadRequest?: () => void
}
```

MidCanvas 컴포넌트 함수 시그니처에 `bgColor` 추가:

```tsx
export default function MidCanvas({
  cards, activeCardIdx, onSelectCard, theme, bgColor, focusedField,
  onFieldFocus, onFieldChange, onImageUploadRequest,
}: Props) {
```

MidCanvas 내부에서 CardRenderer를 호출하는 곳에 `bgColor` 전달. (파일을 읽어 CardRenderer 호출 위치를 찾아 `bgColor={bgColor ?? '#111111'}` 추가)

- [ ] **Step 2: 에디터 페이지에 handleBgColorChange 추가**

`web/src/app/editor/[jobId]/page.tsx` — `handleThemeChange` 아래에 추가:

```tsx
const handleBgColorChange = useCallback((bgColor: string) => {
  setLocalData((prev) => {
    const base = prev ?? apiData?.cardData
    if (!base) return prev
    const updated = { ...base, bg_color: bgColor }
    saveNow(updated)
    return updated
  })
}, [apiData, saveNow])
```

- [ ] **Step 3: RightPanel에 bgColor props 전달**

`page.tsx` 의 `<RightPanel ...>` 부분:

```tsx
<RightPanel
  jobId={jobId}
  activeCard={cards[activeCardIdx]}
  onImageUpdate={handleImageUpdate}
  imageUploadRequested={imageUploadRequested}
  onImageUploadHandled={() => setImageUploadRequested(false)}
  currentThemePrimary={cardData?.theme?.primary}
  recommendedThemeKey={cardData?.recommended_theme_key}
  onThemeChange={handleThemeChange}
  bgColor={cardData?.bg_color ?? '#111111'}
  onBgColorChange={handleBgColorChange}
/>
```

- [ ] **Step 4: MidCanvas에 bgColor 전달**

`page.tsx` 의 `<MidCanvas ...>` 부분에 추가:

```tsx
<MidCanvas
  jobId={jobId}
  cards={cards}
  activeCardIdx={activeCardIdx}
  onSelectCard={setActiveCardIdx}
  theme={cardData?.theme}
  bgColor={cardData?.bg_color ?? '#111111'}
  isDemo={isDemo}
  focusedField={focusedField}
  onFieldFocus={(field) => setFocusedField(field)}
  onFieldChange={handleFieldChange}
  onImageUploadRequest={() => setImageUploadRequested(true)}
/>
```

- [ ] **Step 5: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음

- [ ] **Step 6: 커밋**

```bash
git add web/src/app/editor/[jobId]/page.tsx web/src/components/editor/MidCanvas.tsx
git commit -m "[WEB] 에디터 페이지 bgColor 상태 관리 + MidCanvas 배선"
```

---

## Task 8: S7 렌더 라우트 배선

**Files:**
- Modify: `web/src/app/render/[jobId]/[cardNum]/page.tsx`

- [ ] **Step 1: render route에 bgColor 전달**

`web/src/app/render/[jobId]/[cardNum]/page.tsx` — `<CardRenderer>` 호출 부분:

```tsx
// 변경 전
<CardRenderer card={card} theme={theme} mode="render" scale={1} />

// 변경 후
<CardRenderer card={card} theme={theme} bgColor={cardData?.bg_color ?? '#111111'} mode="render" scale={1} />
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add web/src/app/render/[jobId]/[cardNum]/page.tsx
git commit -m "[WEB] 렌더 라우트 bgColor 전달 — PNG 내보내기에 배경색 반영"
```

---

## Task 9: 통합 테스트 (브라우저 확인)

- [ ] **Step 1: 백엔드 + 프론트엔드 서버 실행**

```bash
# 터미널 1
cd backend && uvicorn main:app --reload --port 8000

# 터미널 2
cd web && npm run dev
```

- [ ] **Step 2: 에디터에서 배경색 변경 확인**

1. `http://localhost:3000/editor/demo` 접속
2. RightPanel → "색상" 섹션 확인
3. "배경" 행 클릭 → ColorPicker 펼쳐짐 확인
4. 프리셋 클릭 → 모든 카드 배경색 즉시 변경 확인
5. `+` 버튼 → 스펙트럼 피커 펼쳐짐 확인
6. HEX 입력 `#0A0F1E` → 딥네이비로 변경 확인
7. RGB 입력 → 색상 변경 확인

- [ ] **Step 3: 테마 강조색 변경 확인**

1. "테마 강조" 행 클릭 → ColorPicker 펼쳐짐 확인
2. 프리셋 스와치 클릭 → 강조색 변경 확인 (배경색 영향 없음)
3. 배경색과 테마 강조색이 독립 동작하는지 확인

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "[WEB] 배경색 변경 + ColorPicker 컴포넌트 통합 완료"
```
