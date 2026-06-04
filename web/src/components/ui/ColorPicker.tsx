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

// ── 기본 프리셋 12개 — 시각적으로 구분 가능한 색상 ─────────────────────────

const DEFAULT_PRESETS = [
  '#111111', '#0A0F1E', '#0D1F12', '#1A0A2E',
  '#1C1008', '#1E293B', '#374151', '#064E3B',
  '#7F1D1D', '#1E3A5F', '#F5F0E8', '#FFFFFF',
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
  const [hexInput, setHexInput] = useState(safeValue)

  const spectrumRef = useRef<HTMLDivElement>(null)
  const hueRef = useRef<HTMLDivElement>(null)
  const draggingSpectrum = useRef(false)
  const draggingHue = useRef(false)

  useEffect(() => {
    if (!isValidHex(value)) return
    const newHsv = hexToHsv(value)
    setHsv(newHsv)
    setHexInput(value)
  }, [value])

  const commit = useCallback((newHsv: [number, number, number]) => {
    const hex = hsvToHex(...newHsv)
    setHsv(newHsv)
    setHexInput(hex)
    onChange(hex)
  }, [onChange])

  const handleSpectrumPointer = useCallback((e: React.PointerEvent) => {
    const el = spectrumRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const s = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const v = Math.max(0, Math.min(1, 1 - (e.clientY - rect.top) / rect.height))
    commit([hsv[0], s, v])
  }, [hsv, commit])

  const handleHuePointer = useCallback((e: React.PointerEvent) => {
    const el = hueRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const h = Math.max(0, Math.min(360, ((e.clientX - rect.left) / rect.width) * 360))
    commit([h, hsv[1], hsv[2]])
  }, [hsv, commit])

  const currentHex = hsvToHex(...hsv)
  const rgb: [number, number, number] = [
    parseInt(currentHex.slice(1, 3), 16),
    parseInt(currentHex.slice(3, 5), 16),
    parseInt(currentHex.slice(5, 7), 16),
  ]
  const hueColor = `hsl(${hsv[0]}, 100%, 50%)`

  return (
    <div style={{ userSelect: 'none' }}>

      {/* 프리셋 스와치 — 6열 그리드 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 5, marginBottom: 10 }}>
        {presets.map((p) => (
          <button
            key={p}
            onClick={() => commit(hexToHsv(p))}
            title={p}
            style={{
              width: '100%', aspectRatio: '1', borderRadius: 5, background: p,
              border: 'none', cursor: 'pointer',
              outline: currentHex.toLowerCase() === p.toLowerCase()
                ? '2px solid var(--brand, #16A34A)'
                : '1px solid rgba(255,255,255,0.18)',
              outlineOffset: 2,
            }}
            aria-label={p}
          />
        ))}
      </div>

      {/* 채도×명도 스펙트럼 — 항상 표시 */}
      <div
        ref={spectrumRef}
        style={{
          height: 120,
          borderRadius: 6,
          background: `linear-gradient(to bottom, transparent, #000), linear-gradient(to right, #fff, ${hueColor})`,
          position: 'relative',
          cursor: 'crosshair',
          marginBottom: 8,
          border: '1px solid rgba(255,255,255,0.12)',
        }}
        onPointerDown={(e) => {
          draggingSpectrum.current = true
          e.currentTarget.setPointerCapture(e.pointerId)
          handleSpectrumPointer(e)
        }}
        onPointerMove={(e) => { if (draggingSpectrum.current) handleSpectrumPointer(e) }}
        onPointerUp={() => { draggingSpectrum.current = false }}
      >
        <div style={{
          position: 'absolute',
          left: `${hsv[1] * 100}%`,
          top: `${(1 - hsv[2]) * 100}%`,
          width: 12, height: 12, borderRadius: '50%',
          border: '2px solid #fff',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.5)',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
        }} />
      </div>

      {/* 색조 슬라이더 — 항상 표시 */}
      <div
        ref={hueRef}
        style={{
          height: 12,
          borderRadius: 6,
          background: 'linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)',
          position: 'relative',
          cursor: 'pointer',
          marginBottom: 10,
          border: '1px solid rgba(255,255,255,0.12)',
        }}
        onPointerDown={(e) => {
          draggingHue.current = true
          e.currentTarget.setPointerCapture(e.pointerId)
          handleHuePointer(e)
        }}
        onPointerMove={(e) => { if (draggingHue.current) handleHuePointer(e) }}
        onPointerUp={() => { draggingHue.current = false }}
      >
        <div style={{
          position: 'absolute', top: '50%',
          left: `${(hsv[0] / 360) * 100}%`,
          width: 14, height: 14, borderRadius: '50%',
          background: hueColor,
          border: '2px solid #fff',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.5)',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
        }} />
      </div>

      {/* HEX 인풋 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 5,
          background: currentHex,
          border: '1px solid rgba(255,255,255,0.2)',
          flexShrink: 0,
        }} />
        <input
          value={hexInput}
          onChange={(e) => {
            const v = e.target.value
            setHexInput(v)
            if (isValidHex(v)) commit(hexToHsv(v))
          }}
          style={{
            flex: 1,
            background: 'var(--canvas-subtle, #1a1a1a)',
            border: '1px solid var(--border-subtle, #333)',
            borderRadius: 6, padding: '4px 8px',
            fontSize: 12, color: 'var(--ink, #fff)',
            fontFamily: 'monospace',
          }}
          spellCheck={false}
        />
      </div>

      {/* RGB 인풋 */}
      <div style={{ display: 'flex', gap: 4 }}>
        {(['R', 'G', 'B'] as const).map((ch, i) => (
          <div key={ch} style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{ch}</div>
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
                width: '100%',
                background: 'var(--canvas-subtle, #1a1a1a)',
                border: '1px solid var(--border-subtle, #333)',
                borderRadius: 4, padding: '3px 2px',
                color: 'var(--ink, #fff)',
                fontFamily: 'monospace', fontSize: 11,
                textAlign: 'center',
              }}
            />
          </div>
        ))}
      </div>

    </div>
  )
}
