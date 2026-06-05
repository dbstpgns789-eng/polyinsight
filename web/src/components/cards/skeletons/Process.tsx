// ④ Process — beat6 제작방법. StepFlow(N단계) + 캡션. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, Caption, StepFlow } from '../skin'
import { parsePipe, joinPipe } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Process(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const steps = parsePipe(fieldValue(card, 'steps'))
  const onStepChange = (i: number, text: string) => {
    const next = [...steps]; next[i] = text
    onFieldChange?.('steps', joinPipe(next))
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <StepFlow steps={steps} mode={mode} onStepChange={onStepChange}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
      <Caption value={fieldValue(card, 'caption')} fieldKey="caption" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'caption'} />
    </CardSurface>
  )
}
