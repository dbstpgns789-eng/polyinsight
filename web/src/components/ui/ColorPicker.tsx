'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

// ── 색상 변환 유틸 ──────────────────────────────────────────────────────────

export function hexToHsv(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const d = max - min
  let h = 0
  if (d !== 0) {
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6
    else if (max === g) h = ((b - r) / d + 2) / 6
    else h = ((r - g) / d + 4) / 6
  }
  return [h * 360, max === 0 ? 0 : d / max, max]
}

export function hsvToHex(h: number, s: number, v: number): string {
  const f = (n: number) => {
    const k = (n + h / 60) % 6
    return v - v * s * Math.max(0, Math.min(k, 4 - k, 1))
  }
  const toHex = (x: number) => Math.round(x * 255).toString(16).padStart(2, '0')
  return `#${toHex(f(5))}${toHex(f(3))}${toHex(f(1))}`
}

function isValidHex(s: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(s)
}

function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  const hex = hsvToHex(h, s, v)
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
}

// ── 기본 프리셋 ─────────────────────────────────────────────────────────────

const DEFAULT_PRESETS = [
  '#111111', '#0A0F1E', '#0D1F12', '#1A0A2E',
  '#1C1008', '#1A1A1A', '#F5F0E8', '#FFFFFF',
]

// ── Props ───────────────────────────────────────────────────────────────────

interface ColorPickerProps {
  value: string
  onChange: (hex: string) => void
  presets?: string[]
}

// ── 컴포넌트 ────────────────────────────────────────────────────────────────

export default function ColorPicker({ value, onChange, presets = DEFAULT_PRESETS }: ColorPickerProps) {
  const safeValue = isValidHex(value) ? value : '#111111'
  const [hsv, setHsv] = useState<[number, number, number]>(() => hexToHsv(safeValue))
  const [open, setOpen] = useState(false)
  const [hexInput, setHexInput] = useState(safeValue)
  const [rgb, setRgb] = useState<[number, number, number]>(() => hsvToRgb(...hexToHsv(safeValue)))

  const spectrumRef = useRef<HTMLDivElement>(null)
  const hueRef = useRef<HTMLDivElement>(null)
  const draggingSpectrum = useRef(false)
  const draggingHue = useRef(false)

  // 외부 value 변경 동기화
  useEffect(() => {
    if (!isValidHex(value)) return
    const newHsv = hexToHsv(value)
    setHsv(newHsv)
    setHexInput(value)
    setRgb(hsvToRgb(...newHsv))
  }, [value])

  const commit = useCallback((newHsv: [number, number, number]) => {
    const hex = hsvToHex(...newHsv)
    setHsv(newHsv)
    setHexInput(hex)
    setRgb(hsvToRgb(...newHsv))
    onChange(hex)
  }, [onChange])

  // 스펙트럼 드래그
  const handleSpectrumPointer = useCallback((e: React.PointerEvent) => {
    const el = spectrumRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const s = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const v = Math.max(0, Math.min(1, 1 - (e.clientY - rect.top) / rect.height))
    commit([hsv[0], s, v])
  }, [hsv, commit])

  // 색조 슬라이더
  const handleHuePointer = useCallback((e: React.PointerEvent) => {
    const el = hueRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const h = Math.max(0, Math.min(360, ((e.clientX - rect.left) / rect.width) * 360))
    commit([h, hsv[1], hsv[2]])
  }, [hsv, commit])

  const currentHex = hsvToHex(...hsv)

  return (
    <div style={{ userSelect: 'none' }}>
      {/* 프리셋 스와치 행 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {presets.map((p) => (
          <button
            key={p}
            onClick={() => { commit(hexToHsv(p)); onChange(p) }}
            style={{
              width: 24, height: 24, borderRadius: '50%', background: p, border: 'none',
              cursor: 'pointer', flexShrink: 0,
              outline: currentHex.toLowerCase() === p.toLowerCase() ? '2px solid var(--brand, #16A34A)' : '1px solid rgba(255,255,255,0.2)',
              outlineOffset: 2,
            }}
            aria-label={p}
          />
        ))}
        {/* 피커 토글 */}
        <button
          onClick={() => setOpen((v) => !v)}
          style={{
            width: 24, height: 24, borderRadius: '50%', background: 'transparent',
            border: '1.5px dashed rgba(255,255,255,0.3)', cursor: 'pointer',
            color: 'rgba(255,255,255,0.5)', fontSize: 14, lineHeight: 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          aria-label="색상 피커 열기"
        >
          {open ? '×' : '+'}
        </button>
      </div>

      {/* Hex 인풋 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: open ? 10 : 0 }}>
        <div style={{ width: 24, height: 24, borderRadius: 4, background: currentHex, border: '1px solid rgba(255,255,255,0.2)', flexShrink: 0 }} />
        <input
          value={hexInput}
          onChange={(e) => {
            const v = e.target.value
            setHexInput(v)
            if (isValidHex(v)) commit(hexToHsv(v))
          }}
          style={{
            flex: 1, background: 'var(--canvas-subtle, #1a1a1a)',
            border: '1px solid var(--border-subtle, #333)',
            borderRadius: 6, padding: '4px 8px',
            fontSize: 12, color: 'var(--ink, #fff)', fontFamily: 'monospace',
          }}
          spellCheck={false}
        />
      </div>

      {/* 스펙트럼 + 슬라이더 (open일 때만) */}
      {open && (
        <div style={{ marginTop: 8, borderRadius: 8, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
          {/* 색조×명도 스펙트럼 */}
          <div
            ref={spectrumRef}
            style={{
              height: 120,
              background: `
                linear-gradient(to bottom, transparent, #000),
                linear-gradient(to right, #fff, hsl(${hsv[0]}, 100%, 50%))
              `,
              position: 'relative', cursor: 'crosshair',
            }}
            onPointerDown={(e) => { draggingSpectrum.current = true; e.currentTarget.setPointerCapture(e.pointerId); handleSpectrumPointer(e) }}
            onPointerMove={(e) => { if (draggingSpectrum.current) handleSpectrumPointer(e) }}
            onPointerUp={() => { draggingSpectrum.current = false }}
          >
            {/* 핸들 */}
            <div style={{
              position: 'absolute',
              left: `${hsv[1] * 100}%`,
              top: `${(1 - hsv[2]) * 100}%`,
              width: 10, height: 10, borderRadius: '50%',
              border: '2px solid #fff', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none',
            }} />
          </div>

          {/* 색조 슬라이더 */}
          <div
            ref={hueRef}
            style={{
              height: 12, margin: '8px 10px 4px',
              background: 'linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)',
              borderRadius: 6, cursor: 'pointer', position: 'relative',
            }}
            onPointerDown={(e) => { draggingHue.current = true; e.currentTarget.setPointerCapture(e.pointerId); handleHuePointer(e) }}
            onPointerMove={(e) => { if (draggingHue.current) handleHuePointer(e) }}
            onPointerUp={() => { draggingHue.current = false }}
          >
            <div style={{
              position: 'absolute', top: '50%', left: `${(hsv[0] / 360) * 100}%`,
              width: 12, height: 12, borderRadius: '50%',
              background: `hsl(${hsv[0]}, 100%, 50%)`,
              border: '2px solid #fff', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none',
            }} />
          </div>

          {/* RGB + HEX 직접 입력 */}
          <div style={{ display: 'flex', gap: 4, padding: '4px 10px 10px', fontSize: 10 }}>
            {(['R', 'G', 'B'] as const).map((ch, i) => (
              <div key={ch} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{ch}</div>
                <input
                  type="number" min={0} max={255}
                  value={rgb[i]}
                  onChange={(e) => {
                    const newRgb: [number, number, number] = [...rgb] as [number, number, number]
                    newRgb[i] = Math.max(0, Math.min(255, Number(e.target.value)))
                    const hex = `#${newRgb.map((v) => v.toString(16).padStart(2, '0')).join('')}`
                    commit(hexToHsv(hex))
                  }}
                  style={{
                    width: '100%', background: 'var(--canvas-subtle, #1a1a1a)',
                    border: '1px solid var(--border-subtle, #333)', borderRadius: 4,
                    padding: '2px 4px', color: 'var(--ink, #fff)',
                    fontFamily: 'monospace', fontSize: 10, textAlign: 'center',
                  }}
                />
              </div>
            ))}
            <div style={{ flex: 1.5, textAlign: 'center' }}>
              <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>HEX</div>
              <input
                value={hexInput}
                onChange={(e) => {
                  const v = e.target.value
                  setHexInput(v)
                  if (isValidHex(v)) commit(hexToHsv(v))
                }}
                style={{
                  width: '100%', background: 'var(--canvas-subtle, #1a1a1a)',
                  border: '1px solid var(--border-subtle, #333)', borderRadius: 4,
                  padding: '2px 4px', color: 'var(--ink, #fff)',
                  fontFamily: 'monospace', fontSize: 10, textAlign: 'center',
                }}
                spellCheck={false}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
