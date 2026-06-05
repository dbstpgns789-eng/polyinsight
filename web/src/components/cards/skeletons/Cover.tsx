// ① Cover — beat1 표지. 상단 텍스트 + 하단 VisualZone 밴드. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Subhead, Caption, VisualZone } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Cover(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginTop: 40 }}>
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
        <Subhead value={fieldValue(card, 'subtitle')} fieldKey="subtitle" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'subtitle'} />
      </div>
      <div style={{ flex: 1, minHeight: 0, marginTop: 32, marginBottom: 24 }}>
        <VisualZone imageUrl={card.image_url} slotKey="cover" mode={mode} onImageRequest={onImageRequest} />
      </div>
      <Caption value={fieldValue(card, 'org')} fieldKey="org" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'org'} />
    </CardSurface>
  )
}
