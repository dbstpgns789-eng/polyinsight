// Ticker — 지표 전광판(N개). 각 = 라벨 + 값 + 등락 화살표. 색 소유는 피부.
// ticker 뼈대가 조립해 쓴다. items = TableRow(attr=지표명, a=값, b=등락 up|down|flat).
import EditableText from '../shared/EditableText'
import type { TableRow } from './parse'

function dirGlyph(dir: string): string {
  const d = dir.trim().toLowerCase()
  if (d === 'up') return '▲'
  if (d === 'down') return '▼'
  return '—'
}
// 등락은 accent(up)/muted(down·flat)로만 — 빨강 금지(세트 톤 유지).
function dirColor(dir: string): string {
  return dir.trim().toLowerCase() === 'up' ? 'var(--set-accent)' : 'var(--set-ink-faint)'
}

interface Props {
  items: TableRow[]
  mode: 'edit' | 'render' | 'thumbnail'
  onItemChange?: (index: number, field: 'attr' | 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function Ticker({ items, mode, onItemChange, onFieldFocus, focusedField }: Props) {
  const cols = items.length <= 3 ? Math.max(1, items.length) : 3
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 'var(--set-gap)', fontFamily: 'var(--set-font)' }}>
      {items.map((it, i) => (
        <div key={i} style={{
          background: 'var(--set-surface)', border: '1px solid var(--set-surface-border)',
          borderRadius: 'var(--set-radius-box)', padding: '24px 26px',
        }}>
          <EditableText
            fieldKey={`tick_label_${i}`} value={it.attr} mode={mode}
            onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'attr', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `tick_label_${i}`}
            style={{ display: 'block', fontSize: 'var(--set-caption)', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--set-ink-muted)', marginBottom: 10, wordBreak: 'keep-all' }}
          />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <EditableText
              fieldKey={`tick_value_${i}`} value={it.a} mode={mode}
              onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `tick_value_${i}`}
              style={{ fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'var(--set-ink-strong)' }}
            />
            <span aria-hidden style={{ fontSize: 'var(--set-body)', fontWeight: 900, color: dirColor(it.b) }}>{dirGlyph(it.b)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
