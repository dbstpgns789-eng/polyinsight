// Eyebrow — 상단 카테고리 라벨. faint, 자간 넓게. 편집 가능.

import EditableText from '../shared/EditableText'

interface EyebrowProps {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

export default function Eyebrow({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: EyebrowProps) {
  return (
    <EditableText
      fieldKey={fieldKey}
      value={value}
      mode={mode}
      onFieldChange={onFieldChange}
      onFieldFocus={onFieldFocus}
      focused={focused}
      style={{
        display: 'block',
        fontFamily: 'var(--set-font)',
        fontSize: 'var(--set-eyebrow)',
        fontWeight: 800,
        letterSpacing: '0.14em',
        color: 'var(--set-ink-faint)',
      }}
    />
  )
}
