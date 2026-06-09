// Subhead — 부제. subhead px, muted. *별표* 구간 accent 강조(render/thumbnail).
'use client'
import EditableText from '../shared/EditableText'
import { parseEmphasis } from './parse'
import { useFieldStyle } from './fieldStyleContext'
import { applyFieldStyle } from '@/lib/fieldStyle'

interface Props {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

export default function Subhead({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: Props) {
  const style = applyFieldStyle({
    display: 'block', fontFamily: 'var(--set-font)', fontSize: 'var(--set-subhead)',
    fontWeight: 600, lineHeight: 1.4, letterSpacing: '-0.015em', color: 'var(--set-ink-muted)', wordBreak: 'keep-all',
  }, useFieldStyle(fieldKey))
  if (mode === 'edit') {
    return (
      <EditableText
        fieldKey={fieldKey} value={value} mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
        style={style}
      />
    )
  }
  return (
    <div style={style}>
      {parseEmphasis(value).map((seg, i) =>
        seg.em
          ? <em key={i} style={{ color: 'var(--set-accent)', fontStyle: 'normal', fontWeight: 700 }}>{seg.text}</em>
          : <span key={i}>{seg.text}</span>
      )}
    </div>
  )
}
