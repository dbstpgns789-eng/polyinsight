// SourceTag — 출처칩. fidelity 정체성 컴포넌트(우리만 필요). S6 grounding과 결합.
// 표면 틴트 + 테두리. 텍스트 편집 가능.
'use client'
import EditableText from '../shared/EditableText'
import { useFieldStyle } from './fieldStyleContext'
import { applyFieldStyle } from '@/lib/fieldStyle'

interface SourceTagProps {
  value: string       // 예: "출처: Cellulose (2024) · Results"
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

export default function SourceTag({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: SourceTagProps) {
  const style = applyFieldStyle({
    fontSize: 'var(--set-caption)',
    fontWeight: 600,
    color: 'var(--set-ink-muted)',
  }, useFieldStyle(fieldKey))
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      alignSelf: 'flex-start',
      background: 'var(--set-surface)',
      border: '1px solid var(--set-surface-border)',
      borderRadius: 'var(--set-radius-pill)',
      padding: '9px 18px',
      fontFamily: 'var(--set-font)',
    }}>
      <span aria-hidden style={{ fontSize: 'var(--set-caption)' }}>📄</span>
      <EditableText
        fieldKey={fieldKey}
        value={value}
        mode={mode}
        onFieldChange={onFieldChange}
        onFieldFocus={onFieldFocus}
        focused={focused}
        style={style}
      />
    </div>
  )
}
