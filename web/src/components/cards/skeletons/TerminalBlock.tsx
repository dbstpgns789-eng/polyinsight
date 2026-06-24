// TerminalBlock — 코드/프롬프트 스니펫 창(CodeBlock). 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, CodeBlock } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function TerminalBlock(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
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
        <CodeBlock code={fieldValue(card, 'code')} lang={fieldValue(card, 'lang')} mode={mode}
          onCodeChange={(v) => onFieldChange?.('code', v)} onLangChange={(v) => onFieldChange?.('lang', v)}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
