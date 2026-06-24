// Funnel — 단계별 좁아지는 퍼널/병목(FunnelChart) + 출처. 피부만 조립. 등록키 'funnel'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, FunnelChart, SourceTag, parseStats, statsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Funnel(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const stages = parseStats(fieldValue(card, 'stages'))
  const onStage = (i: number, field: 'label' | 'value' | 'unit', text: string) => {
    const next = stages.map((s, idx) => (idx === i ? { ...s, [field]: text } : s))
    onFieldChange?.('stages', statsToRaw(next))
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
        <FunnelChart stages={stages} bottleneck={fieldValue(card, 'bottleneck')} mode={mode} onStageChange={onStage}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
      <SourceTag value={fieldValue(card, 'source_ref')} fieldKey="source_ref" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'source_ref'} />
    </CardSurface>
  )
}
