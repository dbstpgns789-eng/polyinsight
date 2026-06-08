// Headline — 카드 제목. *별표* 구간을 accent 강조(em)로 렌더.
'use client'
import EditableText from '../shared/EditableText'
import { parseEmphasis } from './parse'
import { useFieldStyle } from './fieldStyleContext'
import { applyFieldStyle } from '@/lib/fieldStyle'

interface HeadlineProps {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

const headlineBase = {
  display: 'block',
  fontFamily: 'var(--set-font)',
  fontSize: 'var(--set-headline)',
  fontWeight: 800,
  lineHeight: 1.16,
  letterSpacing: '-0.025em',
  color: 'var(--set-ink-strong)',
  wordBreak: 'keep-all' as const,
}

export default function Headline({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: HeadlineProps) {
  const style = applyFieldStyle(headlineBase, useFieldStyle(fieldKey))
  if (mode === 'edit') {
    return (
      <EditableText
        fieldKey={fieldKey} value={value} mode={mode} multiline
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
        style={style}
      />
    )
  }
  return (
    <div style={style}>
      {parseEmphasis(value).map((seg, i) =>
        seg.em
          ? <em key={i} style={{ color: 'var(--set-accent)', fontStyle: 'normal' }}>{seg.text}</em>
          : <span key={i}>{seg.text}</span>
      )}
    </div>
  )
}
