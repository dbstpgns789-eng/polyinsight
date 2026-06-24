// DoDont — 이렇게 마세요 vs 이렇게 하세요(PairColumns, O/X). 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, PairColumns, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function DoDont(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const dont = parsePairs(fieldValue(card, 'dont'))
  const doItems = parsePairs(fieldValue(card, 'do'))
  const onItem = (side: 'left' | 'right', i: number, field: 'a' | 'b', text: string) => {
    if (side === 'left') {
      const next = dont.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
      onFieldChange?.('dont', pairsToRaw(next))
    } else {
      const next = doItems.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
      onFieldChange?.('do', pairsToRaw(next))
    }
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
        <PairColumns
          left={{ label: '이렇게 마세요', mark: '✗', items: dont, prefix: 'dont' }}
          right={{ label: '이렇게 하세요', mark: '✓', items: doItems, prefix: 'do', highlight: true }}
          mode={mode} onItemChange={onItem} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
