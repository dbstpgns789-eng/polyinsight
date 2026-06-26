// TechGrid — 기술/도구 생태계 타일(TechTiles). 피부만 조립. 등록키 'tech_grid'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, TechTiles, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function TechGrid(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const items = parsePairs(fieldValue(card, 'items'))
  const onItem = (i: number, field: 'a' | 'b', text: string) => {
    const next = items.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
    onFieldChange?.('items', pairsToRaw(next))
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
        <TechTiles items={items} mode={mode} onItemChange={onItem}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
