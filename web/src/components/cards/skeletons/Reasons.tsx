// ⑥ Reasons — beat4 왜 이 소재. FeatureColumn(N개 세로근거). 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, FeatureColumn, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Reasons(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const pairs = parsePairs(fieldValue(card, 'reasons'))
  const items = pairs.map((p) => ({ title: p.a, body: p.b }))
  const onItemChange = (i: number, field: 'title' | 'body', text: string) => {
    const next = pairs.map((p, idx) => (idx === i ? (field === 'title' ? { ...p, a: text } : { ...p, b: text }) : p))
    onFieldChange?.('reasons', pairsToRaw(next))
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: 32 }}>
        <FeatureColumn items={items} mode={mode} onItemChange={onItemChange}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
