// Subhead — 부제. subhead px, muted.
import EditableText from '../shared/EditableText'

interface Props {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

export default function Subhead({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: Props) {
  return (
    <EditableText
      fieldKey={fieldKey} value={value} mode={mode}
      onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
      style={{
        display: 'block', fontFamily: 'var(--set-font)', fontSize: 'var(--set-subhead)',
        fontWeight: 600, lineHeight: 1.4, color: 'var(--set-ink-muted)', wordBreak: 'keep-all',
      }}
    />
  )
}
