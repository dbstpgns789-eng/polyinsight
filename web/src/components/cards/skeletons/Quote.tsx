// Quote — 핵심 주장/인용. 큰 인용문(PullQuote) + 출처. 임팩트·저장 유도. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, PullQuote, Caption } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Quote(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 28 }}>
        <PullQuote value={fieldValue(card, 'quote')} fieldKey="quote" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'quote'} />
        <Caption value={fieldValue(card, 'attribution')} fieldKey="attribution" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'attribution'} />
      </div>
    </CardSurface>
  )
}
