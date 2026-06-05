// ⑦ Grid — beat8 응용. IconChip N개 2열 격자 + 선택 본문. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Body, IconChip, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Grid(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const pairs = parsePairs(fieldValue(card, 'items'))
  const onCellChange = (i: number, field: 'a' | 'b', text: string) => {
    const next = pairs.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
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
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 32, alignContent: 'center' }}>
        {pairs.map((p, i) => (
          <IconChip key={i} index={i + 1} label={p.a} sub={p.b} mode={mode}
            onLabelChange={(t) => onCellChange(i, 'a', t)}
            onSubChange={(t) => onCellChange(i, 'b', t)}
            onFieldFocus={onFieldFocus} focusedField={focusedField} />
        ))}
      </div>
      <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
    </CardSurface>
  )
}
