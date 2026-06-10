'use client'
import type { FieldStyle } from '@/types/editor'
import { TRACKING_MIN, TRACKING_MAX, clampTracking } from '@/lib/fieldStyle'

interface Props {
  value?: FieldStyle
  onChange: (patch: Partial<FieldStyle>) => void
  onReset: () => void
}

const SIZES: NonNullable<FieldStyle['size']>[] = ['S', 'M', 'L', 'XL']
const ALIGNS: NonNullable<FieldStyle['align']>[] = ['left', 'center', 'right']
const COLORS: { key: NonNullable<FieldStyle['color']>; label: string; css: string }[] = [
  { key: 'ink-strong', label: '진하게', css: 'var(--ink)' },
  { key: 'ink-muted', label: '약하게', css: 'var(--ink-3)' },
  { key: 'accent', label: '강조', css: 'var(--brand)' },
]
const ALIGN_ICON: Record<string, string> = { left: 'format_align_left', center: 'format_align_center', right: 'format_align_right' }

const segBtn = (active: boolean): React.CSSProperties => ({
  flex: 1, padding: '6px 0', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
  border: '1px solid var(--border-subtle)',
  background: active ? 'var(--brand)' : 'var(--canvas)',
  color: active ? '#fff' : 'var(--ink-2)',
})
const rowLabel: React.CSSProperties = { fontSize: 10, fontWeight: 700, color: 'var(--ink-3)', marginBottom: 4, display: 'block' }

export default function ElementStyleControls({ value, onChange, onReset }: Props) {
  const fs = value ?? {}
  const hasAny = !!value && Object.keys(value).length > 0
  const sizeVal = fs.size ?? 'M'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 크기 */}
      <div>
        <span style={rowLabel}>크기</span>
        <div style={{ display: 'flex', gap: 4 }}>
          {SIZES.map((s) => (
            <button key={s} type="button" style={segBtn(sizeVal === s)} onClick={() => onChange({ size: s })}>{s}</button>
          ))}
        </div>
      </div>

      {/* 자간 */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={rowLabel}>자간</span>
          <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>{(fs.tracking ?? 0).toFixed(2)}em</span>
        </div>
        <input type="range" min={TRACKING_MIN} max={TRACKING_MAX} step={0.01} value={fs.tracking ?? 0}
          onChange={(e) => onChange({ tracking: clampTracking(parseFloat(e.target.value)) })}
          className="w-full h-1 rounded-lg appearance-none cursor-pointer accent-forest-green bg-canvas-muted" />
      </div>

      {/* 굵기 + 정렬 */}
      <div style={{ display: 'flex', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <span style={rowLabel}>굵기</span>
          <div style={{ display: 'flex', gap: 4 }}>
            <button type="button" style={segBtn((fs.weight ?? 'regular') === 'regular')} onClick={() => onChange({ weight: 'regular' })}>R</button>
            <button type="button" style={{ ...segBtn(fs.weight === 'bold'), fontWeight: 800 }} onClick={() => onChange({ weight: 'bold' })}>B</button>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <span style={rowLabel}>정렬</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {ALIGNS.map((a) => (
              <button key={a} type="button" style={segBtn(fs.align === a)} onClick={() => onChange({ align: a })}>
                <span className="material-symbols-outlined" style={{ fontSize: 15 }}>{ALIGN_ICON[a]}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 색 */}
      <div>
        <span style={rowLabel}>색</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {COLORS.map((c) => (
            <button key={c.key} type="button" aria-label={c.label} onClick={() => onChange({ color: c.key })}
              style={{
                width: 26, height: 26, borderRadius: 6, cursor: 'pointer', background: c.css,
                border: fs.color === c.key ? '2px solid var(--ink)' : '1px solid var(--border-subtle)',
              }} />
          ))}
        </div>
      </div>

      {/* 되돌리기 */}
      <button type="button" onClick={onReset} disabled={!hasAny}
        style={{
          marginTop: 2, fontSize: 11, fontWeight: 600, color: hasAny ? 'var(--brand)' : 'var(--ink-3)',
          background: 'none', border: 'none', cursor: hasAny ? 'pointer' : 'default', textAlign: 'left', padding: 0,
          textDecoration: hasAny ? 'underline' : 'none',
        }}>
        ↺ AI 제안값으로 되돌리기
      </button>
    </div>
  )
}
