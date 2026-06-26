// Timeline(skeleton) — 진화 타임라인(skin Timeline). 피부만 조립. 등록키 'timeline'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Timeline, parseTableRows, tableRowsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function TimelineCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const events = parseTableRows(fieldValue(card, 'events'))
  const onEvent = (i: number, field: 'attr' | 'a' | 'b', text: string) => {
    const next = events.map((e, idx) => (idx === i ? { ...e, [field]: text } : e))
    onFieldChange?.('events', tableRowsToRaw(next))
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
        <Timeline events={events} mode={mode} onEventChange={onEvent}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
