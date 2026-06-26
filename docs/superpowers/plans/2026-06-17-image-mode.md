# image_mode 구현 계획 (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `image_mode` 필드를 CardSlot에 추가하고, backdrop·ghost·none 3가지 이미지 렌더 방식을 구현한다.

**Architecture:** CardFrame이 `imageMode`에 따라 이미지 레이어를 렌더하고, CardSurface는 backdrop/ghost 모드에서 배경을 투명하게 만들며, VisualZone은 `imageMode !== 'box'`일 때 자기 자신을 숨긴다. S6 Writer가 카드마다 `image_mode`를 출력한다.

**Tech Stack:** Python/Pydantic (backend), React/TypeScript (frontend), Next.js 15 App Router

---

## 파일 맵

| 작업 | 파일 |
|---|---|
| 생성 | `web/src/components/cards/skin/imageModeContext.tsx` |
| 수정 | `backend/core/models.py` |
| 수정 | `web/src/types/editor.ts` |
| 수정 | `web/src/components/cards/CardRenderer.tsx` |
| 수정 | `web/src/components/cards/CardFrame.tsx` |
| 수정 | `web/src/components/cards/skin/CardSurface.tsx` |
| 수정 | `web/src/components/cards/skin/VisualZone.tsx` |
| 수정 | `web/src/components/editor/RightPanel.tsx` |
| 수정 | `web/src/app/editor/[jobId]/page.tsx` |
| 수정 | `backend/agents/s6/prompts.py` |
| 수정 | `backend/agents/s6/writer.py` |

---

## Task 1: 백엔드 — CardSlot에 image_mode 추가

**Files:**
- Modify: `backend/core/models.py:76-96`

- [ ] **Step 1: IMAGE_MODES 상수에 Phase 1 값 추가, CardSlot에 필드 삽입**

`backend/core/models.py`의 `VALID_TEMPLATE_TYPES` 아래, `CardSlot` 클래스 수정:

```python
# backend/core/models.py

IMAGE_MODES = {"box", "backdrop", "ghost", "none"}
# Phase 2: "band", "split", "panel" — 추후 추가

class CardSlot(BaseModel):
    """단일 카드. template_type이 어떤 HTML 템플릿을 쓸지 결정."""
    card_num: int
    template_type: str
    fields: Dict[str, FieldValue]
    image_url: str | None = None
    focal: Dict[str, float] | None = None
    image_fit: str | None = None
    image_mode: str = "box"                      # 신규. 기본 'box' (하위 호환)
    field_styles: Dict[str, FieldStyle] | None = None
```

- [ ] **Step 2: 검증 — 기존 CardSlot 생성이 하위 호환됨을 확인**

```bash
cd backend
python -c "
from core.models import CardSlot, FieldValue
# image_mode 없이 생성 → 기본 'box'
slot = CardSlot(card_num=1, template_type='cover_v2', fields={})
assert slot.image_mode == 'box', f'기본값 오류: {slot.image_mode}'
# image_mode 지정
slot2 = CardSlot(card_num=2, template_type='feature', fields={}, image_mode='backdrop')
assert slot2.image_mode == 'backdrop'
print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add backend/core/models.py
git commit -m "[BE] CardSlot에 image_mode 필드 추가 (기본 box, Phase 1: backdrop/ghost/none)"
```

---

## Task 2: 프론트엔드 타입 — Card 인터페이스에 image_mode 추가

**Files:**
- Modify: `web/src/types/editor.ts:18-26`

- [ ] **Step 1: Card 인터페이스에 image_mode 추가**

```typescript
// web/src/types/editor.ts

export type ImageMode = 'box' | 'backdrop' | 'ghost' | 'none'

export interface Card {
  card_num: number
  template_type: string
  image_url?: string
  focal?: { x: number; y: number }
  image_fit?: 'cover' | 'contain'
  image_mode?: ImageMode          // 신규. undefined === 'box' (하위 호환)
  fields?: Record<string, FieldValue>
  field_styles?: Record<string, FieldStyle>
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개

- [ ] **Step 3: 커밋**

```bash
git add web/src/types/editor.ts
git commit -m "[FE] Card 타입에 image_mode 필드 추가"
```

---

## Task 3: 신규 파일 — imageModeContext.tsx

**Files:**
- Create: `web/src/components/cards/skin/imageModeContext.tsx`

- [ ] **Step 1: Context 파일 생성**

```typescript
// web/src/components/cards/skin/imageModeContext.tsx
import { createContext, useContext, type ReactNode } from 'react'
import type { ImageMode } from '@/types/editor'

const ImageModeContext = createContext<ImageMode>('box')

export function ImageModeProvider({ value, children }: { value: ImageMode; children: ReactNode }) {
  return <ImageModeContext.Provider value={value}>{children}</ImageModeContext.Provider>
}

export function useImageMode(): ImageMode {
  return useContext(ImageModeContext)
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/cards/skin/imageModeContext.tsx
git commit -m "[FE] ImageModeContext 추가 (VisualZone/CardSurface가 imageMode 읽음)"
```

---

## Task 4: CardRenderer — ImageModeProvider 래핑 + CardFrame에 imageUrl/imageMode 전달

**Files:**
- Modify: `web/src/components/cards/CardRenderer.tsx`

- [ ] **Step 1: CardRenderer 수정**

```typescript
// web/src/components/cards/CardRenderer.tsx
'use client'

import CardFrame from './CardFrame'
import { CARD_COMPONENTS } from './index'
import { FieldStylesProvider } from './skin/fieldStyleContext'
import { ImageModeProvider } from './skin/imageModeContext'
import { getSet } from './skin/sets'
import type { ImageMode } from '@/types/editor'
import type { CardComponentProps } from './types'

interface CardRendererProps extends CardComponentProps {
  scale?: number
  bgColor?: string
  accentColor?: string
  fontPairing?: string
  setKey?: string
}

export default function CardRenderer({ scale = 1, bgColor, accentColor, fontPairing, setKey, ...props }: CardRendererProps) {
  const { card } = props
  const Component = CARD_COMPONENTS[card.template_type]
  const imageMode: ImageMode = card.image_mode ?? 'box'

  return (
    <FieldStylesProvider value={card.field_styles ?? {}}>
      <ImageModeProvider value={imageMode}>
        <CardFrame
          set={getSet(setKey)}
          bgColor={bgColor}
          accentColor={accentColor}
          fontPairing={fontPairing}
          scale={scale}
          imageUrl={card.image_url}
          imageMode={imageMode}
        >
          {Component ? <Component {...props} /> : <UnimplementedTemplate templateType={card.template_type} />}
        </CardFrame>
      </ImageModeProvider>
    </FieldStylesProvider>
  )
}

function UnimplementedTemplate({ templateType }: { templateType: string }) {
  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--set-bg, #111111)',
      color: '#666', fontFamily: 'Noto Sans KR, sans-serif', gap: 16,
    }}>
      <div style={{ fontSize: 80 }}>🚧</div>
      <div style={{ fontSize: 40, fontWeight: 700 }}>{templateType}</div>
      <div style={{ fontSize: 22, color: '#999' }}>Phase 2에서 구현 예정</div>
    </div>
  )
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개 (CardFrame에 아직 imageUrl/imageMode props 없어 에러 발생 → Task 5 후 해소)

- [ ] **Step 3: 커밋 (Task 5 직후로 미뤄도 됨)**

---

## Task 5: CardFrame — backdrop / ghost / none 이미지 레이어 렌더

**Files:**
- Modify: `web/src/components/cards/CardFrame.tsx`

- [ ] **Step 1: CardFrame props에 imageUrl/imageMode 추가, 레이어 렌더 구현**

```typescript
// web/src/components/cards/CardFrame.tsx
import { type CSSProperties, type ReactNode } from 'react'
import styles from './cards.module.css'
import { REPORT_LIGHT_SET, type CardSet } from './skin/sets'
import { FONT_PAIRINGS } from './fontPairings'
import type { ImageMode } from '@/types/editor'

const CARD_SIZE = 1080

interface CardFrameProps {
  bgColor?: string
  accentColor?: string
  fontPairing?: string
  scale?: number
  set?: CardSet
  imageUrl?: string      // 신규
  imageMode?: ImageMode  // 신규. 기본 'box'
  children: ReactNode
  className?: string
}

export default function CardFrame({
  bgColor, accentColor, fontPairing, scale = 1,
  set = REPORT_LIGHT_SET,
  imageUrl, imageMode = 'box',
  children, className,
}: CardFrameProps) {
  const wrapperStyle: CSSProperties = {
    width: CARD_SIZE * scale,
    height: CARD_SIZE * scale,
    position: 'relative',
    overflow: 'hidden',
  }

  // backdrop 모드: 이미지 위 텍스트가 보이도록 잉크 토큰을 흰색으로 오버라이드
  const backdropTokenOverride: CSSProperties = imageMode === 'backdrop' ? {
    '--set-ink-strong': '#ffffff',
    '--set-ink-muted': 'rgba(255,255,255,0.72)',
    '--set-ink-faint': 'rgba(255,255,255,0.45)',
    '--set-surface': 'rgba(255,255,255,0.12)',
    '--set-surface-border': 'rgba(255,255,255,0.20)',
  } as CSSProperties : {}

  const innerStyle: CSSProperties = {
    ...set.tokens,
    ...(bgColor ? { '--set-bg': bgColor, '--set-bg-gradient': bgColor } : {}),
    ...(accentColor ? { '--set-accent': accentColor } : {}),
    ...(fontPairing && FONT_PAIRINGS[fontPairing] ? { '--set-font': FONT_PAIRINGS[fontPairing] } : {}),
    ...backdropTokenOverride,
    width: CARD_SIZE,
    height: CARD_SIZE,
    position: 'relative',
    overflow: 'hidden',
    // backdrop/ghost 모드: CardFrame 베이스 배경은 세트 색 유지 (ghost의 깊이감)
    // none/box 모드: 기존과 동일
    background: 'var(--set-bg-gradient)',
    fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    boxSizing: 'border-box',
    ...(scale === 1 ? {} : { transform: `scale(${scale})`, transformOrigin: 'top left' }),
  } as CSSProperties

  return (
    <div style={wrapperStyle} className={className}>
      <div className={styles.scope} style={innerStyle}>

        {/* ── backdrop: 풀블리드 이미지 + 하단 그라디언트 오버레이 ── */}
        {imageMode === 'backdrop' && imageUrl && (
          <>
            <img
              src={imageUrl}
              alt=""
              style={{
                position: 'absolute', inset: 0,
                width: '100%', height: '100%',
                objectFit: 'cover', zIndex: 0,
                pointerEvents: 'none',
              }}
            />
            <div style={{
              position: 'absolute', inset: 0, zIndex: 1,
              background: 'linear-gradient(180deg, rgba(0,0,0,0.08) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0.52) 68%, rgba(0,0,0,0.88) 100%)',
              pointerEvents: 'none',
            }} />
          </>
        )}

        {/* ── ghost: 풀블리드 이미지 극저투명도 ── */}
        {imageMode === 'ghost' && imageUrl && (
          <img
            src={imageUrl}
            alt=""
            style={{
              position: 'absolute', inset: 0,
              width: '100%', height: '100%',
              objectFit: 'cover', opacity: 0.09, zIndex: 1,
              pointerEvents: 'none',
            }}
          />
        )}

        {/* ── 스켈레톤 — 항상 최상위 ── */}
        <div style={{ position: 'relative', zIndex: 2, width: '100%', height: '100%' }}>
          {children}
        </div>
      </div>
    </div>
  )
}

export { styles as cardStyles }
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/cards/CardRenderer.tsx web/src/components/cards/CardFrame.tsx
git commit -m "[FE] CardFrame/Renderer에 imageMode 렌더 레이어 추가 (backdrop·ghost·none)"
```

---

## Task 6: CardSurface — backdrop·ghost 모드에서 배경 투명화

**Files:**
- Modify: `web/src/components/cards/skin/CardSurface.tsx`

- [ ] **Step 1: useImageMode 훅으로 배경·그림자 조건 처리**

```typescript
// web/src/components/cards/skin/CardSurface.tsx
import type { ReactNode } from 'react'
import BgMotif from './BgMotif'
import { useImageMode } from './imageModeContext'

interface CardSurfaceProps {
  children: ReactNode
  motif?: boolean
}

export default function CardSurface({ children, motif = true }: CardSurfaceProps) {
  const imageMode = useImageMode()
  const isOverlay = imageMode === 'backdrop' || imageMode === 'ghost'

  return (
    <div style={{
      width: '100%', height: '100%',
      position: 'relative', overflow: 'hidden',
      // overlay 모드: 이미지가 CardFrame에 있으므로 배경 투명
      background: isOverlay ? 'transparent' : 'var(--set-bg-gradient)',
      fontFamily: 'var(--set-font)',
      color: 'var(--set-ink-strong)',
      boxSizing: 'border-box',
      boxShadow: isOverlay ? 'none' : 'var(--set-card-glow, none)',
    }}>
      {/* overlay 모드에서는 모티프(배경 패턴)도 숨김 */}
      {motif && !isOverlay && <BgMotif />}
      <div style={{
        position: 'relative', zIndex: 1,
        width: '100%', height: '100%',
        padding: 'var(--set-pad)',
        boxSizing: 'border-box',
        display: 'flex', flexDirection: 'column',
      }}>
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/cards/skin/CardSurface.tsx
git commit -m "[FE] CardSurface — backdrop/ghost 모드에서 배경 투명화"
```

---

## Task 7: VisualZone — box 모드 외 자동 숨김

**Files:**
- Modify: `web/src/components/cards/skin/VisualZone.tsx`

- [ ] **Step 1: useImageMode 체크 → box 아니면 null**

```typescript
// web/src/components/cards/skin/VisualZone.tsx
import EditableImage from '../shared/EditableImage'
import type { Focal } from '@/lib/focal'
import { useImageMode } from './imageModeContext'

interface VisualZoneProps {
  imageUrl?: string
  slotKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  focal?: Focal
  fit?: 'cover' | 'contain'
  radius?: boolean
  onImageRequest?: (slotKey: string) => void
  onFocalChange?: (focal: Focal) => void
  onFitChange?: (fit: 'cover' | 'contain') => void
}

export default function VisualZone({
  imageUrl, slotKey, mode, focal, fit, radius = true,
  onImageRequest, onFocalChange, onFitChange,
}: VisualZoneProps) {
  const imageMode = useImageMode()
  // box 모드가 아니면 CardFrame이 이미지를 처리 — 이 박스는 숨긴다
  if (imageMode !== 'box') return null

  return (
    <div style={{
      width: '100%', height: '100%', overflow: 'hidden',
      borderRadius: radius ? 'var(--set-radius-box)' : 0,
      background: 'var(--set-surface)',
    }}>
      <EditableImage
        imageUrl={imageUrl}
        slotKey={slotKey}
        mode={mode}
        objectFit={fit ?? 'cover'}
        focal={focal}
        onImageRequest={onImageRequest}
        onFocalChange={onFocalChange}
        onFitChange={onFitChange}
      />
    </div>
  )
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/cards/skin/VisualZone.tsx
git commit -m "[FE] VisualZone — imageMode != box 시 자동 숨김 (CardFrame이 이미지 처리)"
```

---

## Task 8: RightPanel — image_mode 선택 UI 추가

**Files:**
- Modify: `web/src/components/editor/RightPanel.tsx`

- [ ] **Step 1: hasSlot 제약 제거 — 모든 카드가 이미지 업로드 가능하도록**

RightPanel.tsx에서 `hasSlot` 관련 두 줄을 찾아 수정:

```typescript
// 기존 (특정 template_type만 이미지 허용)
const slotMeta = activeCard ? getSlotMeta(activeCard.template_type) : null
const hasSlot  = slotMeta?.type !== 'none'

// 변경 (모든 카드가 이미지 업로드 가능 — image_mode로 제어)
const hasSlot = true
```

`slotMeta` / `getSlotMeta` import도 더 이상 쓰이지 않으면 제거.
(SlotDiagram 컴포넌트가 `slotMeta`를 쓰면 그 부분만 유지.)

- [ ] **Step 2: Props에 currentImageMode / onImageModeChange 추가**

`RightPanel.tsx`의 `interface Props` 블록에 두 줄 추가:

```typescript
// 기존 Props 인터페이스 끝에 추가
  currentImageMode?: string
  onImageModeChange: (mode: string) => void
```

- [ ] **Step 2: 컴포넌트 파라미터에 두 필드 추가**

```typescript
export default function RightPanel({
  // 기존 파라미터들...
  currentImageMode, onImageModeChange,
}: Props) {
```

- [ ] **Step 3: 이미지 섹션 안에 mode 선택 UI 삽입**

RightPanel의 이미지 업로드 UI가 있는 `openSection === 'image'` 블록을 찾아, 업로드 영역 아래에 다음 블록 추가:

```typescript
{/* image_mode 선택 */}
<div style={{ marginTop: 16 }}>
  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 8 }}>
    이미지 배치 방식
  </div>
  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
    {([
      { key: 'box',      label: '박스',     desc: '기존 영역 안에' },
      { key: 'backdrop', label: '풀블리드',  desc: '카드 전체 배경' },
      { key: 'ghost',    label: '고스트',    desc: '흐릿하게 배경에' },
      { key: 'none',     label: '이미지 없음', desc: '텍스트만' },
    ] as { key: string; label: string; desc: string }[]).map(({ key, label, desc }) => {
      const active = (currentImageMode ?? 'box') === key
      return (
        <button
          key={key}
          type="button"
          onClick={() => onImageModeChange(key)}
          style={{
            padding: '8px 10px', borderRadius: 8, cursor: 'pointer', textAlign: 'left',
            border: active ? '1.5px solid var(--brand)' : '1px solid var(--border-subtle)',
            background: active ? 'var(--brand-soft)' : 'var(--canvas)',
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: active ? 'var(--brand)' : 'var(--ink)' }}>{label}</div>
          <div style={{ fontSize: 10, color: 'var(--ink-3)', marginTop: 2 }}>{desc}</div>
        </button>
      )
    })}
  </div>
</div>
```

- [ ] **Step 4: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 발생 (page.tsx에서 onImageModeChange를 아직 안 넘김) → Task 9 후 해소

- [ ] **Step 5: 커밋 (Task 9 완료 후)**

---

## Task 9: editor page.tsx — handleImageModeUpdate 추가 + RightPanel에 연결

**Files:**
- Modify: `web/src/app/editor/[jobId]/page.tsx`

- [ ] **Step 1: handleImageModeUpdate 콜백 추가**

`handleFitUpdate` 함수 바로 다음에 추가:

```typescript
const handleImageModeUpdate = useCallback((mode: string) => {
  setLocalData((prev) => {
    const base = prev ?? apiData?.cardData
    if (!base) return prev
    const updatedCards = base.cards.map((card, idx) => {
      if (idx !== activeCardIdx) return card
      return { ...card, image_mode: mode as Card['image_mode'] }
    })
    const updated = { ...base, cards: updatedCards }
    debouncedSave(updated)
    return updated
  })
}, [activeCardIdx, apiData, debouncedSave])
```

파일 상단 import에 `Card` 타입이 없으면 추가:
```typescript
import type { Card } from '@/types/editor'
```

- [ ] **Step 2: RightPanel에 두 props 전달**

page.tsx의 `<RightPanel>` JSX에 두 줄 추가:

```typescript
<RightPanel
  // 기존 props들...
  currentImageMode={cards[activeCardIdx]?.image_mode ?? 'box'}
  onImageModeChange={handleImageModeUpdate}
/>
```

- [ ] **Step 3: 타입 체크**

```bash
cd web && npx tsc --noEmit
```
Expected: 에러 0개

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/editor/RightPanel.tsx web/src/app/editor/[jobId]/page.tsx
git commit -m "[FE] RightPanel — image_mode 선택 UI + 에디터 상태 연결"
```

---

## Task 10: S6 Writer — image_mode 출력 추가

**Files:**
- Modify: `backend/agents/s6/prompts.py`
- Modify: `backend/agents/s6/writer.py`

- [ ] **Step 1: prompts.py — TEMPLATE_SPEC 끝에 image_mode 지침 추가**

`backend/agents/s6/prompts.py`에서 `TEMPLATE_SPEC` 문자열 끝(닫는 `"""` 앞)에 추가:

```python
TEMPLATE_SPEC = """
... (기존 내용 유지) ...

[image_mode 선택 — 카드마다 필수]
각 카드의 "image_mode" 필드를 반드시 출력하라.

  "backdrop" — 사진·현장 이미지가 있고 시각 임팩트가 핵심인 카드 (표지, 강한 훅)
  "ghost"    — 데이터/수치 카드에 이미지가 있지만 텍스트 가독성이 우선일 때
  "none"     — 이미지가 없거나 텍스트 전용 카드 (process, reasons, bigstat_compare 등)
  "box"      — 이미지를 박스 안에 담아 텍스트와 구분할 때 (폴백 기본값)

이미지 없는 카드(bigstat_compare·process_v2·reasons·grid_v2·callout·multistat·definition·compare_table)는 반드시 "none".
이미지 있는 표지/statement/feature 카드는 "backdrop" 우선 검토.
"""
```

- [ ] **Step 2: writer.py — 파싱 시 image_mode 읽기**

`writer.py`의 `cards.append(CardSlot(...))` 줄을 다음으로 교체:

```python
# 기존
cards.append(CardSlot(card_num=card_num, template_type=tt, fields=fields))

# 변경
raw_mode = raw_card.get("image_mode", "box")
safe_mode = raw_mode if raw_mode in {"box", "backdrop", "ghost", "none"} else "box"
cards.append(CardSlot(
    card_num=card_num,
    template_type=tt,
    fields=fields,
    image_mode=safe_mode,
))
```

- [ ] **Step 3: 빠른 smoke test (DEV_MOCK_LLM)**

```bash
cd backend
DEV_MOCK_LLM=True python -c "
import asyncio
from agents.s6.mock import mock_storyboard, mock_cards
from core.models import PaperMetadata
meta = PaperMetadata(title='테스트 논문', authors=['홍길동'], year='2025')
sb = mock_storyboard(5, meta)
wr = mock_cards(sb.storyboard, meta)
for c in wr.cards:
    print(f'card {c.card_num} {c.template_type}: image_mode={c.image_mode}')
"
```
Expected: 각 카드마다 image_mode 값 출력 (mock은 기본 'box')

- [ ] **Step 4: 커밋**

```bash
git add backend/agents/s6/prompts.py backend/agents/s6/writer.py
git commit -m "[BE] S6 Writer — image_mode 출력 지침 추가 및 파싱"
```

---

## Task 11: 시각 검증 (E2E)

- [ ] **Step 1: 개발 서버 시작**

```bash
# 터미널 1
cd backend && uvicorn main:app --reload --port 8000

# 터미널 2
cd web && npm run dev
```

- [ ] **Step 2: 기존 카드 회귀 확인**

브라우저에서 `http://localhost:3000/editor/<임의 jobId>` 열기.
- image_mode 미설정(box) 카드 → 기존과 동일하게 보임 ✓
- VisualZone이 있는 스켈레톤(cover, feature) → 박스 안에 이미지 정상 표시 ✓

- [ ] **Step 3: backdrop 모드 검증**

RightPanel 이미지 섹션 → "풀블리드" 선택.
- 이미지 업로드 후: 카드 전체 배경에 이미지, 하단 어둡게, 텍스트 흰색 ✓
- 이미지 없이 backdrop 선택: 세트 색상 배경 그대로 (빈 카드 아님) ✓

- [ ] **Step 4: ghost 모드 검증**

"고스트" 선택.
- 이미지 업로드 후: 이미지가 배경에 흐릿하게(약 9% 불투명도), 텍스트·수치 명확 ✓
- BgMotif(배경 패턴)가 사라지고 이미지만 보임 ✓

- [ ] **Step 5: none 모드 검증**

"이미지 없음" 선택.
- VisualZone 완전히 숨겨짐, 이미지 없는 텍스트 카드 ✓

- [ ] **Step 6: 최종 커밋**

```bash
git add .
git commit -m "[FE][BE] image_mode Phase 1 완료 — backdrop·ghost·none 구현 + 에디터 UI"
```

---

## Phase 2 예고 (이번 슬라이스 제외)

- `band`: CardFrame 상단 이미지 존 + 하단 스켈레톤 존
- `split`: CardFrame 좌우 분할 구조
- `panel`: 풀블리드 이미지 + 하단 불투명 패널 안에 스켈레톤

Phase 2는 CardSurface의 렌더 영역 제한이 필요 → 별도 슬라이스.
