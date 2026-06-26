// Mythbuster — 오해 vs 진실 핑퐁(FaceoffRows). 통념 깨기. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, FaceoffRows, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Mythbuster(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const pairs = parsePairs(fieldValue(card, 'pairs'))
  const onRow = (i: number, field: 'a' | 'b', text: string) => {
    const next = pairs.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
    onFieldChange?.('pairs', pairsToRaw(next))
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
        <FaceoffRows rows={pairs} leftLabel="오해" rightLabel="진실" mode={mode}
          onRowChange={onRow} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
