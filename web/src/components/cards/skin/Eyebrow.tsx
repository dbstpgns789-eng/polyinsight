// Eyebrow — 상단 카테고리 키커. 앞에 악센트 틱 + 굵은 트래킹 라벨. 편집 가능.
'use client'
import EditableText from '../shared/EditableText'
import { useFieldStyle } from './fieldStyleContext'
import { applyFieldStyle } from '@/lib/fieldStyle'

interface EyebrowProps {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

export default function Eyebrow({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: EyebrowProps) {
  const style = applyFieldStyle({
    display: 'block', fontFamily: 'var(--set-font)', fontSize: 'var(--set-eyebrow)',
    fontWeight: 800, letterSpacing: '0.12em', color: 'var(--set-ink-muted)',
  }, useFieldStyle(fieldKey))
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span aria-hidden style={{ width: 26, height: 4, borderRadius: 2, background: 'var(--set-accent)', flex: '0 0 auto' }} />
      <EditableText
        fieldKey={fieldKey} value={value} mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focused}
        style={style}
      />
    </div>
  )
}
