// RadarChart(skeleton) — 다축 성능 비교(skin RadarChart) + 출처. 피부만 조립. 등록키 'radar_chart'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, RadarChart, SourceTag, parseTableRows, tableRowsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function RadarChartCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const axes = parseTableRows(fieldValue(card, 'axes'))
  const onAxis = (i: number, field: 'attr' | 'a' | 'b', text: string) => {
    const next = axes.map((r, idx) => (idx === i ? { ...r, [field]: text } : r))
    onFieldChange?.('axes', tableRowsToRaw(next))
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: 24 }}>
        <RadarChart axes={axes} mode={mode} onAxisChange={onAxis}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
      <SourceTag value={fieldValue(card, 'source_ref')} fieldKey="source_ref" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'source_ref'} />
    </CardSurface>
  )
}
