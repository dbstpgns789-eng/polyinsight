// IconChip — Grid 항목 칩. accent 번호 배지 + 라벨 + 보조텍스트. 표면 틴트.
import EditableText from '../shared/EditableText'

interface IconChipProps {
  index: number          // 1-based 번호
  label: string
  sub: string
  mode: 'edit' | 'render' | 'thumbnail'
  onLabelChange?: (text: string) => void
  onSubChange?: (text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function IconChip({ index, label, sub, mode, onLabelChange, onSubChange, onFieldFocus, focusedField }: IconChipProps) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 12,
      background: 'var(--set-surface)', border: '1px solid var(--set-surface-border)',
      borderRadius: 'var(--set-radius-box)', padding: 28, fontFamily: 'var(--set-font)',
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 'var(--set-radius-pill)',
        background: 'var(--set-accent)', color: 'var(--set-accent-ink)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 'var(--set-subhead)', fontWeight: 900, flexShrink: 0,
      }}>{index}</div>
      <EditableText
        fieldKey={`chip_label_${index}`} value={label} mode={mode}
        onFieldChange={onLabelChange ? (_fk, v) => onLabelChange(v) : undefined}
        onFieldFocus={onFieldFocus} focused={focusedField === `chip_label_${index}`}
        style={{ display: 'block', fontSize: 'var(--set-subhead)', fontWeight: 800, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
      />
      <EditableText
        fieldKey={`chip_sub_${index}`} value={sub} mode={mode}
        onFieldChange={onSubChange ? (_fk, v) => onSubChange(v) : undefined}
        onFieldFocus={onFieldFocus} focused={focusedField === `chip_sub_${index}`}
        style={{ display: 'block', fontSize: 'var(--set-caption)', fontWeight: 500, color: 'var(--set-ink-muted)', wordBreak: 'keep-all' }}
      />
    </div>
  )
}
