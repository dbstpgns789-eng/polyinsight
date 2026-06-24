// GrowthChart — 우상향 추세 꺾은선(LineChart) + 출처. 피부만 조립. 등록키 'growth_chart'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, LineChart, SourceTag, parsePairs, pairsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function GrowthChart(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const series = parsePairs(fieldValue(card, 'series'))
  const onPoint = (i: number, field: 'a' | 'b', text: string) => {
    const next = series.map((p, idx) => (idx === i ? { ...p, [field]: text } : p))
    onFieldChange?.('series', pairsToRaw(next))
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
        <LineChart series={series} mode={mode} onPointChange={onPoint}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
      <SourceTag value={fieldValue(card, 'source_ref')} fieldKey="source_ref" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'source_ref'} />
    </CardSurface>
  )
}
