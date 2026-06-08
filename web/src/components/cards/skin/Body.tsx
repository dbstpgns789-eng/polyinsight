// Body — 본문. body px, muted, multiline.
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

export default function Body({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: Props) {
  const style = applyFieldStyle({
    display: 'block', fontFamily: 'var(--set-font)', fontSize: 'var(--set-body)',
    fontWeight: 400, lineHeight: 1.62, letterSpacing: '-0.01em', color: 'var(--set-ink-muted)', wordBreak: 'keep-all',
  }, useFieldStyle(fieldKey))
  return (
    <EditableText
      fieldKey={fieldKey} value={value} mode={mode} multiline
      onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
      style={style}
    />
  )
}
