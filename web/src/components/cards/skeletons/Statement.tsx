// ② Statement — beat2 훅 / beat3 한계. 큰 질문 + 본문 + (선택) 하단 이미지 밴드.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Body, VisualZone } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Statement(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest, onFocalChange, onFitChange } = props
  const showImage = !!card.image_url || mode === 'edit'
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      {showImage ? (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28, marginTop: 40 }}>
            <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
              onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
            <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
              onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
          </div>
          <div style={{ flex: 1, minHeight: 0, marginTop: 32 }}>
            <VisualZone imageUrl={card.image_url} slotKey="statement" mode={mode} focal={card.focal} fit={card.image_fit}
              onImageRequest={onImageRequest} onFocalChange={onFocalChange} onFitChange={onFitChange} />
          </div>
        </>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 32 }}>
          <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
            onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
          <Body value={fieldValue(card, 'body')} fieldKey="body" mode={mode}
            onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'body'} />
        </div>
      )}
    </CardSurface>
  )
}
