// TradeOffMatrix — 장점 vs 한계 두 컬럼(PairColumns). 논문 limitation. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, PairColumns, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function TradeOffMatrix(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const pros = parsePairs(fieldValue(card, 'pros'))
  const cons = parsePairs(fieldValue(card, 'cons'))
  const onItem = (side: 'left' | 'right', i: number, field: 'a' | 'b', text: string) => {
    if (side === 'left') {
      const next = pros.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
      onFieldChange?.('pros', pairsToRaw(next))
    } else {
      const next = cons.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
      onFieldChange?.('cons', pairsToRaw(next))
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
          left={{ label: '장점', mark: '✓', items: pros, prefix: 'pros', highlight: true }}
          right={{ label: '한계', mark: '△', items: cons, prefix: 'cons' }}
          mode={mode} onItemChange={onItem} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
