// LineChart — 우상향 추세 꺾은선. SVG(읽기전용 파생) + 편집 가능한 x:y 범례. 색 소유는 피부.
// growth_chart 뼈대가 조립해 쓴다. series = Pair(a=x라벨, b=y값).
import EditableText from '../shared/EditableText'
import { compareBarValue } from './parse'
import type { Pair } from './parse'

interface Props {
  series: Pair[]
  mode: 'edit' | 'render' | 'thumbnail'
  onPointChange?: (index: number, field: 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

const W = 760
const H = 320
const PAD = 36

export default function LineChart({ series, mode, onPointChange, onFieldFocus, focusedField }: Props) {
  const valid = series.filter((p) => p.a.length > 0)
  const ys = valid.map((p) => compareBarValue(p.b))
  const max = Math.max(1, ...ys)
  const min = Math.min(0, ...ys)
  const span = max - min || 1
  const n = valid.length
  const x = (i: number) => PAD + (n <= 1 ? 0 : (i * (W - 2 * PAD)) / (n - 1))
  const y = (v: number) => H - PAD - ((v - min) / span) * (H - 2 * PAD)
  const pts = valid.map((p, i) => `${x(i)},${y(compareBarValue(p.b))}`)

  return (
    <div style={{ fontFamily: 'var(--set-font)' }}>
      {n >= 2 && (
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
          {/* 기준선 */}
          <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} style={{ stroke: 'var(--set-surface-border)' }} strokeWidth={1.5} />
          {/* 면적 */}
          <polygon points={`${PAD},${H - PAD} ${pts.join(' ')} ${W - PAD},${H - PAD}`}
            style={{ fill: 'var(--set-accent)', opacity: 0.12 }} />
          {/* 선 */}
          <polyline points={pts.join(' ')} style={{ fill: 'none', stroke: 'var(--set-accent)' }} strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
          {/* 점 */}
          {valid.map((p, i) => (
            <circle key={i} cx={x(i)} cy={y(compareBarValue(p.b))} r={7} style={{ fill: 'var(--set-accent)' }} />
          ))}
        </svg>
      )}
      {/* 편집 범례 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, marginTop: 18 }}>
        {valid.map((p, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'baseline', gap: 8,
            background: 'var(--set-surface)', border: '1px solid var(--set-surface-border)',
            borderRadius: 'var(--set-radius-pill)', padding: '8px 16px',
          }}>
            <EditableText
              fieldKey={`line_x_${i}`} value={p.a} mode={mode}
              onFieldChange={onPointChange ? (_fk, v) => onPointChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `line_x_${i}`}
              style={{ fontSize: 'var(--set-caption)', fontWeight: 600, color: 'var(--set-ink-muted)' }}
            />
            <EditableText
              fieldKey={`line_y_${i}`} value={p.b} mode={mode}
              onFieldChange={onPointChange ? (_fk, v) => onPointChange(i, 'b', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `line_y_${i}`}
              style={{ fontSize: 'var(--set-caption)', fontWeight: 900, color: 'var(--set-accent)' }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
