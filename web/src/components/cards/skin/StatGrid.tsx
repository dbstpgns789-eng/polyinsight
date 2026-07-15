// StatGrid — 핵심 수치 N개 그리드(2~4). 각 = 값+단위(accent) + 라벨. 적응형. 편집 가능.
import EditableText from '../shared/EditableText'
import type { StatItem } from './parse'

interface Props {
  items: StatItem[]
  mode: 'edit' | 'render' | 'thumbnail'
  onItemChange?: (index: number, field: 'label' | 'value' | 'unit', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function StatGrid({ items, mode, onItemChange, onFieldFocus, focusedField }: Props) {
  const n = items.length
  // 행당 목표 개수: 1~3→그대로 한 줄, 4→2x2, 5+→3/행.
  // flex-grow로 마지막 행이 폭을 꽉 채워 '데드 스페이스(고아 박스)'를 없앤다.
  const perRow = n <= 3 ? Math.max(1, n) : n === 4 ? 2 : 3
  const basis = `calc(${100 / perRow}% - var(--set-gap) * ${(perRow - 1) / perRow})`
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--set-gap)', fontFamily: 'var(--set-font)' }}>
      {items.map((it, i) => (
        <div key={i} style={{
          flex: `1 1 ${basis}`, minWidth: 0,
          background: 'var(--set-surface)', border: '1px solid var(--set-surface-border)',
          borderRadius: 'var(--set-radius-box)', padding: '30px 32px',
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <EditableText
              fieldKey={`stat_value_${i}`} value={it.value} mode={mode}
              onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'value', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `stat_value_${i}`}
              style={{ fontSize: 'var(--set-headline)', fontWeight: 900, lineHeight: 1, letterSpacing: '-0.03em', color: 'var(--set-ink-strong)' }}
            />
            <EditableText
              fieldKey={`stat_unit_${i}`} value={it.unit} mode={mode}
              onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'unit', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `stat_unit_${i}`}
              style={{ fontSize: 'var(--set-subhead)', fontWeight: 800, color: 'var(--set-accent)' }}
            />
          </div>
          <EditableText
            fieldKey={`stat_label_${i}`} value={it.label} mode={mode} multiline
            onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'label', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `stat_label_${i}`}
            style={{ display: 'block', marginTop: 12, fontSize: 'var(--set-caption)', fontWeight: 500, lineHeight: 1.4, color: 'var(--set-ink-muted)', wordBreak: 'keep-all' }}
          />
        </div>
      ))}
    </div>
  )
}
