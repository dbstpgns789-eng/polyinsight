// Caption — 캡션. caption px, faint.
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

export default function Caption({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: Props) {
  const style = applyFieldStyle({
    display: 'block', fontFamily: 'var(--set-font)', fontSize: 'var(--set-caption)',
    fontWeight: 500, lineHeight: 1.5, letterSpacing: '-0.005em', color: 'var(--set-ink-faint)',
  }, useFieldStyle(fieldKey))
  return (
    <EditableText
      fieldKey={fieldKey} value={value} mode={mode}
      onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
      style={style}
    />
  )
}
