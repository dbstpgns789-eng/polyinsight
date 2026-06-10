// DataTable — 속성별 A vs B 비교 표(2~4행). 헤더(A=accent, B=muted) + 행. 편집 가능.
import EditableText from '../shared/EditableText'
import type { TableRow } from './parse'

interface Props {
  rows: TableRow[]
  colA: string
  colB: string
  mode: 'edit' | 'render' | 'thumbnail'
  onRowChange?: (index: number, field: 'attr' | 'a' | 'b', text: string) => void
  onHeaderChange?: (field: 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

const cell: React.CSSProperties = { padding: '18px 20px', display: 'flex', alignItems: 'center', minWidth: 0 }
const GRID = '1.2fr 1fr 1fr'

export default function DataTable({ rows, colA, colB, mode, onRowChange, onHeaderChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ fontFamily: 'var(--set-font)', borderRadius: 'var(--set-radius-box)', overflow: 'hidden', border: '1px solid var(--set-surface-border)' }}>
      {/* 헤더 */}
      <div style={{ display: 'grid', gridTemplateColumns: GRID, background: 'var(--set-surface)' }}>
        <div style={cell} />
        <div style={cell}>
          <EditableText fieldKey="col_a" value={colA} mode={mode}
            onFieldChange={onHeaderChange ? (_fk, v) => onHeaderChange('a', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === 'col_a'}
            style={{ fontSize: 'var(--set-caption)', fontWeight: 800, color: 'var(--set-accent)' }} />
        </div>
        <div style={cell}>
          <EditableText fieldKey="col_b" value={colB} mode={mode}
            onFieldChange={onHeaderChange ? (_fk, v) => onHeaderChange('b', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === 'col_b'}
            style={{ fontSize: 'var(--set-caption)', fontWeight: 700, color: 'var(--set-ink-muted)' }} />
        </div>
      </div>
      {/* 행 */}
      {rows.map((r, i) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: GRID, borderTop: '1px solid var(--set-surface-border)' }}>
          <div style={cell}>
            <EditableText fieldKey={`row_attr_${i}`} value={r.attr} mode={mode}
              onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'attr', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `row_attr_${i}`}
              style={{ fontSize: 'var(--set-caption)', fontWeight: 700, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }} />
          </div>
          <div style={cell}>
            <EditableText fieldKey={`row_a_${i}`} value={r.a} mode={mode}
              onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `row_a_${i}`}
              style={{ fontSize: 'var(--set-caption)', fontWeight: 800, color: 'var(--set-accent)', wordBreak: 'keep-all' }} />
          </div>
          <div style={cell}>
            <EditableText fieldKey={`row_b_${i}`} value={r.b} mode={mode}
              onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'b', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `row_b_${i}`}
              style={{ fontSize: 'var(--set-caption)', fontWeight: 500, color: 'var(--set-ink-muted)', wordBreak: 'keep-all' }} />
          </div>
        </div>
      ))}
    </div>
  )
}
