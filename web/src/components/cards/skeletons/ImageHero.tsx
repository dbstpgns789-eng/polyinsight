// ImageHero — 논문 figure/그래프를 주인공으로. 큰 VisualZone + 제목 + 캡션. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Caption, VisualZone } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function ImageHero(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest, onFocalChange, onFitChange } = props
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
      <div style={{ flex: 1, minHeight: 0, marginTop: 28, marginBottom: 16 }}>
        <VisualZone imageUrl={card.image_url} slotKey="image_hero" mode={mode} focal={card.focal} fit={card.image_fit}
          onImageRequest={onImageRequest} onFocalChange={onFocalChange} onFitChange={onFitChange} />
      </div>
      <Caption value={fieldValue(card, 'caption')} fieldKey="caption" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'caption'} />
    </CardSurface>
  )
}
