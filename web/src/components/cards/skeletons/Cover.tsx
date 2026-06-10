// ① Cover — beat1 표지. 상단 텍스트 + 하단 VisualZone 밴드. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Subhead, Caption, VisualZone } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Cover(props: CardComponentProps) {
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginTop: 40 }}>
            <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
              onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
            <Subhead value={fieldValue(card, 'subtitle')} fieldKey="subtitle" mode={mode}
              onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'subtitle'} />
          </div>
          <div style={{ flex: 1, minHeight: 0, marginTop: 32, marginBottom: 24 }}>
            <VisualZone imageUrl={card.image_url} slotKey="cover" mode={mode} focal={card.focal} fit={card.image_fit} onImageRequest={onImageRequest} onFocalChange={onFocalChange} onFitChange={onFitChange} />
          </div>
        </>
      ) : (
        // 이미지 없으면 죽은 spacer 대신 제목 블록을 세로 중앙 정렬(의도된 여백)
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
            onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
          <Subhead value={fieldValue(card, 'subtitle')} fieldKey="subtitle" mode={mode}
            onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'subtitle'} />
        </div>
      )}
      <Caption value={fieldValue(card, 'org')} fieldKey="org" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'org'} />
    </CardSurface>
  )
}
