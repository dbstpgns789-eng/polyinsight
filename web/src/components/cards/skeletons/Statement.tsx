// ② Statement — beat2 훅 / beat3 한계. 큰 질문 + 본문. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Body } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Statement(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 32 }}>
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
        <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
      </div>
    </CardSurface>
  )
}
