// PullQuote — 큰 인용문(따옴표 감쌈) + *별표* accent 강조. quote 뼈대용.
'use client'
import EditableText from '../shared/EditableText'
import { parseEmphasis } from './parse'

interface Props {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

const baseStyle = {
  display: 'block',
  fontFamily: 'var(--set-font)',
  fontSize: 'calc(var(--set-subhead) * 1.55)',
  fontWeight: 800,
  lineHeight: 1.32,
  letterSpacing: '-0.02em',
  color: 'var(--set-ink-strong)',
  wordBreak: 'keep-all' as const,
}

export default function PullQuote({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: Props) {
  if (mode === 'edit') {
    return (
      <EditableText
        fieldKey={fieldKey} value={value} mode={mode} multiline
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
        style={baseStyle}
      />
    )
  }
  return (
    <div style={baseStyle}>
      <span aria-hidden style={{ color: 'var(--set-accent)' }}>“</span>
      {parseEmphasis(value).map((seg, i) =>
        seg.em
          ? <em key={i} style={{ color: 'var(--set-accent)', fontStyle: 'normal' }}>{seg.text}</em>
          : <span key={i}>{seg.text}</span>
      )}
      <span aria-hidden style={{ color: 'var(--set-accent)' }}>”</span>
    </div>
  )
}
