// Caption — 캡션. caption px, faint.
import EditableText from '../shared/EditableText'

interface Props {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

export default function Caption({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: Props) {
  return (
    <EditableText
      fieldKey={fieldKey} value={value} mode={mode}
      onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
      style={{
        display: 'block', fontFamily: 'var(--set-font)', fontSize: 'var(--set-caption)',
        fontWeight: 500, lineHeight: 1.5, color: 'var(--set-ink-faint)',
      }}
    />
  )
}
