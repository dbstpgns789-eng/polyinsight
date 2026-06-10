// MultiStat — 핵심 수치 2~4개 한 화면(StatGrid). 결과 여러 지표. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, StatGrid, SourceTag, parseStats, statsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function MultiStat(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const items = parseStats(fieldValue(card, 'stats'))
  const onItemChange = (i: number, field: 'label' | 'value' | 'unit', text: string) => {
    const next = items.map((s, idx) => (idx === i ? { ...s, [field]: text } : s))
    onFieldChange?.('stats', statsToRaw(next))
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
        <StatGrid items={items} mode={mode} onItemChange={onItemChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
      <SourceTag value={fieldValue(card, 'source_ref')} fieldKey="source_ref" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'source_ref'} />
    </CardSurface>
  )
}
