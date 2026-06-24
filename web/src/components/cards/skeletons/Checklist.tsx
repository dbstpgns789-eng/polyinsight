// Checklist(skeleton) — 실행 체크리스트(skin Checklist). 피부만 조립. 등록키 'checklist'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Checklist } from '../skin'
import { parsePipe, joinPipe } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function ChecklistCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const items = parsePipe(fieldValue(card, 'items'))
  const onItem = (i: number, text: string) => {
    const next = [...items]; next[i] = text
    onFieldChange?.('items', joinPipe(next))
  }
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: 28 }}>
        <Checklist items={items} mode={mode} onItemChange={onItem}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
