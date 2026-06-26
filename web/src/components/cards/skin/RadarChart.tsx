// RadarChart — 다축 레이더(우리 vs 기존). SVG 도형(읽기전용 파생) + 편집 가능한 범례. 색 소유는 피부.
// radar_chart 뼈대가 조립해 쓴다. axes = TableRow(attr=축라벨, a=우리값, b=기존값).
// 값 편집은 범례에서 → 원본 필드 재파싱 → 도형 갱신.
import EditableText from '../shared/EditableText'
import { compareBarValue } from './parse'
import type { TableRow } from './parse'

interface Props {
  axes: TableRow[]
  mode: 'edit' | 'render' | 'thumbnail'
  onAxisChange?: (index: number, field: 'attr' | 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

const SIZE = 360
const C = SIZE / 2
const R = 132

function polygon(axes: TableRow[], pick: (r: TableRow) => number, max: number): string {
  return axes.map((r, i) => {
    const ang = (-90 + (i * 360) / axes.length) * (Math.PI / 180)
    const mag = max > 0 ? (pick(r) / max) * R : 0
    return `${C + mag * Math.cos(ang)},${C + mag * Math.sin(ang)}`
  }).join(' ')
}

export default function RadarChart({ axes, mode, onAxisChange, onFieldFocus, focusedField }: Props) {
  const valid = axes.filter((a) => a.attr.length > 0)
  const max = Math.max(1, ...valid.flatMap((r) => [compareBarValue(r.a), compareBarValue(r.b)]))
  const grid = valid.length >= 3 ? valid : []  // 최소 3축이어야 폐곡선

  return (
    <div style={{ display: 'flex', gap: 'var(--set-gap)', alignItems: 'center', fontFamily: 'var(--set-font)' }}>
      {grid.length > 0 && (
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ flexShrink: 0 }}>
          {/* 그리드 링 */}
          {[0.33, 0.66, 1].map((t, k) => (
            <polygon key={k}
              points={grid.map((_, i) => {
                const ang = (-90 + (i * 360) / grid.length) * (Math.PI / 180)
                return `${C + t * R * Math.cos(ang)},${C + t * R * Math.sin(ang)}`
              }).join(' ')}
              style={{ fill: 'none', stroke: 'var(--set-surface-border)' }} strokeWidth={1.5} />
          ))}
          {/* 축선 */}
          {grid.map((_, i) => {
            const ang = (-90 + (i * 360) / grid.length) * (Math.PI / 180)
            return <line key={i} x1={C} y1={C} x2={C + R * Math.cos(ang)} y2={C + R * Math.sin(ang)}
              style={{ stroke: 'var(--set-surface-border)' }} strokeWidth={1} />
          })}
          {/* 기존(muted) */}
          <polygon points={polygon(grid, (r) => compareBarValue(r.b), max)}
            style={{ fill: 'var(--set-ink-faint)', stroke: 'var(--set-ink-muted)', opacity: 0.28 }} strokeWidth={2} />
          {/* 우리(accent) */}
          <polygon points={polygon(grid, (r) => compareBarValue(r.a), max)}
            style={{ fill: 'var(--set-accent)', stroke: 'var(--set-accent)', fillOpacity: 0.22 }} strokeWidth={3} />
        </svg>
      )}
      {/* 편집 범례 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
        {valid.map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <EditableText
              fieldKey={`radar_axis_${i}`} value={r.attr} mode={mode}
              onFieldChange={onAxisChange ? (_fk, v) => onAxisChange(i, 'attr', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `radar_axis_${i}`}
              style={{ flex: 1, fontSize: 'var(--set-caption)', fontWeight: 700, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
            />
            <EditableText
              fieldKey={`radar_our_${i}`} value={r.a} mode={mode}
              onFieldChange={onAxisChange ? (_fk, v) => onAxisChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `radar_our_${i}`}
              style={{ width: 64, textAlign: 'right', fontSize: 'var(--set-caption)', fontWeight: 900, color: 'var(--set-accent)' }}
            />
            <EditableText
              fieldKey={`radar_base_${i}`} value={r.b} mode={mode}
              onFieldChange={onAxisChange ? (_fk, v) => onAxisChange(i, 'b', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `radar_base_${i}`}
              style={{ width: 64, textAlign: 'right', fontSize: 'var(--set-caption)', fontWeight: 600, color: 'var(--set-ink-muted)' }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
