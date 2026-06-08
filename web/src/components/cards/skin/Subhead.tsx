// Subhead — 부제. subhead px, muted.
'use client'
import EditableText from '../shared/EditableText'
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
  return (
    <EditableText
      fieldKey={fieldKey} value={value} mode={mode}
      onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
      style={style}
    />
  )
}
