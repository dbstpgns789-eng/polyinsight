// Callout — "이것만 기억" 한 줄 강조. 중앙정렬, 저장 유도. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Body } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Callout(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}><BrandMark /></div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', gap: 26 }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
        <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
      </div>
    </CardSurface>
  )
}
