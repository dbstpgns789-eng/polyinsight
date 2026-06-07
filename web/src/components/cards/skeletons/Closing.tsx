// ⑧ Closing — beat9(마무리/협력). 텍스트 + (선택) 하단 중앙 이미지 밴드 + 출처.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Body, SourceTag, AccentDivider, VisualZone } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Closing(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest, onFocalChange, onFitChange } = props
  const showImage = !!card.image_url || mode === 'edit'
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}><BrandMark /></div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
        <AccentDivider />
        <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
        {showImage && (
          <div style={{ width: '100%', maxWidth: 620, alignSelf: 'center', aspectRatio: '16 / 7', marginTop: 8 }}>
            <VisualZone imageUrl={card.image_url} slotKey="closing_v2" mode={mode} focal={card.focal} fit={card.image_fit}
              onImageRequest={onImageRequest} onFocalChange={onFocalChange} onFitChange={onFitChange} />
          </div>
        )}
      </div>
      <SourceTag value={fieldValue(card, 'source_ref')} fieldKey="source_ref" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'source_ref'} />
    </CardSurface>
  )
}
