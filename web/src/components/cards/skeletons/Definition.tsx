// Definition — 개념 풀이. 용어 + 쉬운 설명 + 한 줄 비유. jargon→쉽게(미션). 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, AccentDivider, Body, Caption } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Definition(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
        <AccentDivider />
        <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
        <Caption value={fieldValue(card, 'caption')} fieldKey="caption" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'caption'} />
      </div>
    </CardSurface>
  )
}
