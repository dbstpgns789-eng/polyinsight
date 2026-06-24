// ABSplit — A vs B 승자 증명(VersusPanels). 피부만 조립. 등록키 'ab_split'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, VersusPanels, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function ABSplit(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const a = parsePairs(fieldValue(card, 'variant_a'))[0] ?? { a: '', b: '' }
  const b = parsePairs(fieldValue(card, 'variant_b'))[0] ?? { a: '', b: '' }
  const winner = fieldValue(card, 'winner').trim().toLowerCase() === 'b' ? 'b' : 'a'
  const onChange = (side: 'a' | 'b', field: 'label' | 'value', text: string) => {
    const cur = side === 'a' ? a : b
    const next = field === 'label' ? { ...cur, a: text } : { ...cur, b: text }
    onFieldChange?.(side === 'a' ? 'variant_a' : 'variant_b', pairsToRaw([next]))
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
        <VersusPanels a={{ label: a.a, value: a.b }} b={{ label: b.a, value: b.b }} winner={winner}
          mode={mode} onChange={onChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
