// PairColumns — 두 개의 독립 라벨 컬럼(각각 제목:본문 리스트). 색 소유는 피부.
// tradeoff_matrix(장점/한계) · do_dont(이렇게마세요/이렇게하세요)가 조립해 쓴다.
import EditableText from '../shared/EditableText'
import type { Pair } from './parse'

export interface PairSide {
  label: string          // 고정 라벨(편집 대상 아님) 예: "장점"
  mark?: string          // 항목 앞 표식 예: "✓" / "✗"
  items: Pair[]
  prefix: string         // fieldKey 프리픽스(좌/우 충돌 방지)
  highlight?: boolean     // accent 강조 컬럼
}

interface Props {
  left: PairSide
  right: PairSide
  mode: 'edit' | 'render' | 'thumbnail'
  onItemChange?: (side: 'left' | 'right', index: number, field: 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

function Column({ side, which, mode, onItemChange, onFieldFocus, focusedField }: {
  side: PairSide; which: 'left' | 'right'
  mode: Props['mode']; onItemChange?: Props['onItemChange']
  onFieldFocus?: Props['onFieldFocus']; focusedField?: Props['focusedField']
}) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 10, alignSelf: 'flex-start',
        fontSize: 'var(--set-caption)', fontWeight: 800, letterSpacing: '0.04em',
        color: side.highlight ? 'var(--set-accent)' : 'var(--set-ink-muted)',
      }}>
        {side.mark && <span aria-hidden>{side.mark}</span>}{side.label}
      </div>
      {side.items.map((it, i) => (
        <div key={i} style={{
          background: 'var(--set-surface)',
          border: side.highlight ? '1.5px solid var(--set-accent)' : '1px solid var(--set-surface-border)',
          borderRadius: 'var(--set-radius-box)', padding: '18px 22px',
        }}>
          <EditableText
            fieldKey={`${side.prefix}_title_${i}`} value={it.a} mode={mode}
            onFieldChange={onItemChange ? (_fk, v) => onItemChange(which, i, 'a', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `${side.prefix}_title_${i}`}
            style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 800, color: 'var(--set-ink-strong)', wordBreak: 'keep-all', marginBottom: 6 }}
          />
          <EditableText
            fieldKey={`${side.prefix}_body_${i}`} value={it.b} mode={mode} multiline
            onFieldChange={onItemChange ? (_fk, v) => onItemChange(which, i, 'b', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `${side.prefix}_body_${i}`}
            style={{ display: 'block', fontSize: 'var(--set-caption)', fontWeight: 500, lineHeight: 1.5, color: 'var(--set-ink-muted)', wordBreak: 'keep-all' }}
          />
        </div>
      ))}
    </div>
  )
}

export default function PairColumns({ left, right, mode, onItemChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', gap: 'var(--set-gap)', fontFamily: 'var(--set-font)', alignItems: 'stretch' }}>
      <Column side={left} which="left" mode={mode} onItemChange={onItemChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      <Column side={right} which="right" mode={mode} onItemChange={onItemChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
    </div>
  )
}
