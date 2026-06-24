// SwipeBait — 다음 장 넘기기 유도(ClippedReveal). 중간 카드 한정. 피부만 조립. 등록키 'swipe_bait'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, ClippedReveal } from '../skin'
import { parsePipe, joinPipe } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function SwipeBait(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const items = parsePipe(fieldValue(card, 'cut_items'))
  const onItem = (i: number, text: string) => {
    const next = [...items]; next[i] = text
    onFieldChange?.('cut_items', joinPipe(next))
  }
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ marginTop: 18 }}>
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: 28 }}>
        <ClippedReveal teaser={fieldValue(card, 'teaser')} items={items} mode={mode}
          onTeaserChange={(v) => onFieldChange?.('teaser', v)} onItemChange={onItem}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
