// Checklist — 실행 체크리스트(N항목). 각 = 체크박스(accent) + 텍스트. 색 소유는 피부.
// checklist 뼈대가 조립해 쓴다. items = string[].
import EditableText from '../shared/EditableText'

interface Props {
  items: string[]
  mode: 'edit' | 'render' | 'thumbnail'
  onItemChange?: (index: number, text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function Checklist({ items, mode, onItemChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontFamily: 'var(--set-font)' }}>
      {items.map((it, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 18,
          background: 'var(--set-surface)', border: '1px solid var(--set-surface-border)',
          borderRadius: 'var(--set-radius-box)', padding: '18px 24px',
        }}>
          <div aria-hidden style={{
            width: 38, height: 38, borderRadius: 9, flexShrink: 0,
            background: 'var(--set-accent)', color: 'var(--set-accent-ink)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 'var(--set-body)', fontWeight: 900,
          }}>✓</div>
          <EditableText
            fieldKey={`check_${i}`} value={it} mode={mode} multiline
            onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `check_${i}`}
            style={{ display: 'block', flex: 1, fontSize: 'var(--set-body)', fontWeight: 600, lineHeight: 1.4, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
          />
        </div>
      ))}
    </div>
  )
}
