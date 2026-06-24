// FaceoffRows — 오해 vs 진실 핑퐁 행(N행). 좌=오해(muted), 우=진실(accent). 색 소유는 피부.
// mythbuster 뼈대가 조립해 쓴다.
import EditableText from '../shared/EditableText'
import type { Pair } from './parse'

interface Props {
  rows: Pair[]           // a=오해, b=진실
  leftLabel: string
  rightLabel: string
  mode: 'edit' | 'render' | 'thumbnail'
  onRowChange?: (index: number, field: 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function FaceoffRows({ rows, leftLabel, rightLabel, mode, onRowChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: 'var(--set-font)' }}>
      {rows.map((r, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'stretch', gap: 14 }}>
          <div style={{
            flex: 1, minWidth: 0, background: 'var(--set-surface)',
            border: '1px solid var(--set-surface-border)', borderRadius: 'var(--set-radius-box)', padding: '18px 22px',
          }}>
            <div style={{ fontSize: 'var(--set-caption)', fontWeight: 800, color: 'var(--set-ink-faint)', marginBottom: 6 }}>{leftLabel}</div>
            <EditableText
              fieldKey={`myth_${i}`} value={r.a} mode={mode} multiline
              onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `myth_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 600, lineHeight: 1.45, color: 'var(--set-ink-muted)', wordBreak: 'keep-all', textDecoration: 'line-through', textDecorationColor: 'var(--set-ink-faint)' }}
            />
          </div>
          <div aria-hidden style={{ alignSelf: 'center', fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'var(--set-accent)', flexShrink: 0 }}>→</div>
          <div style={{
            flex: 1, minWidth: 0, background: 'var(--set-surface)',
            border: '1.5px solid var(--set-accent)', borderRadius: 'var(--set-radius-box)', padding: '18px 22px',
          }}>
            <div style={{ fontSize: 'var(--set-caption)', fontWeight: 800, color: 'var(--set-accent)', marginBottom: 6 }}>{rightLabel}</div>
            <EditableText
              fieldKey={`truth_${i}`} value={r.b} mode={mode} multiline
              onFieldChange={onRowChange ? (_fk, v) => onRowChange(i, 'b', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `truth_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 700, lineHeight: 1.45, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
