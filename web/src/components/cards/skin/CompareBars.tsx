// CompareBars — 비교 막대. 배열 N개를 받아 배치(적응형). 최댓값 대비 너비.
// primary=true → accent 골드. CompareRow 타입·파싱은 ./parse.

import EditableText from '../shared/EditableText'
import { compareBarValue } from './parse'
import type { CompareRow } from './parse'

interface CompareBarsProps {
  rows: CompareRow[]
  mode: 'edit' | 'render' | 'thumbnail'
  onRowChange?: (index: number, field: 'label' | 'value', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function CompareBars({ rows, mode, onRowChange, onFieldFocus, focusedField }: CompareBarsProps) {
  const max = rows.reduce((m, r) => Math.max(m, compareBarValue(r.value)), 0) || 1

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, fontFamily: 'var(--set-font)' }}>
      {rows.map((r, i) => {
        const pct = Math.max(4, compareBarValue(r.value) / max * 100)
        return (
          <div key={i}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
              <EditableText
                fieldKey={`bar_label_${i}`}
                value={r.label}
                mode={mode}
                onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'label', v) : undefined}
                onFieldFocus={onFieldFocus}
                focused={focusedField === `bar_label_${i}`}
                style={{
                  fontSize: 'var(--set-caption)',
                  fontWeight: r.primary ? 700 : 500,
                  color: r.primary ? 'var(--set-ink-strong)' : 'var(--set-ink-muted)',
                }}
              />
              <EditableText
                fieldKey={`bar_value_${i}`}
                value={r.value}
                mode={mode}
                onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'value', v) : undefined}
                onFieldFocus={onFieldFocus}
                focused={focusedField === `bar_value_${i}`}
                style={{
                  fontSize: 'var(--set-caption)',
                  fontWeight: 800,
                  color: r.primary ? 'var(--set-accent)' : 'var(--set-ink-muted)',
                }}
              />
            </div>
            <div style={{ height: 24, borderRadius: 999, background: 'var(--set-surface)', overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`, height: '100%', borderRadius: 999,
                background: r.primary ? 'var(--set-accent)' : 'var(--set-ink-faint)',
              }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
