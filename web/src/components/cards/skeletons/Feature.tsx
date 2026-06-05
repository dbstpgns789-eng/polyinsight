// ③ Feature — beat5 혁신. 좌 텍스트 + 우 VisualZone 2단. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Body, AccentDivider, VisualZone } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Feature(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ flex: 1, display: 'flex', gap: 40, alignItems: 'stretch', marginTop: 24 }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
            onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
          <AccentDivider />
          <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
            onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <VisualZone imageUrl={card.image_url} slotKey="feature" mode={mode} onImageRequest={onImageRequest} />
        </div>
      </div>
    </CardSurface>
  )
}
