'use client'

import { useRef, useEffect, useState } from 'react'
import { getSlotMeta } from '@/lib/imageSlots'
import type { SlotType } from '@/lib/imageSlots'
import type { Card, CardTheme } from '@/types/editor'
import ColorPicker, { hexToHsv, hsvToHex } from '@/components/ui/ColorPicker'

interface Props {
  jobId: string
  activeCard?: Card
  onImageUpdate: (imageUrl: string | null) => void
  imageUploadRequested?: boolean
  onImageUploadHandled?: () => void
  currentThemePrimary?: string
  recommendedThemeKey?: string
  onThemeChange: (theme: CardTheme) => void
  bgColor: string
  onBgColorChange: (hex: string) => void
}

// ── 슬롯 위치 다이어그램 ───────────────────────────────────────────────────
function SlotDiagram({ type }: { type: SlotType }) {
  const base: React.CSSProperties = {
    borderRadius: 8, background: 'var(--canvas-muted)',
    overflow: 'hidden', position: 'relative', width: '100%', height: 68,
    border: '1px solid var(--border-subtle)',
  }
  const img: React.CSSProperties = {
    background: 'var(--brand)', opacity: 0.35, position: 'absolute',
  }
  const line = (w: string, h = 4): React.CSSProperties => ({
    height: h, width: w, borderRadius: 2, background: 'var(--border-soft)',
  })

  if (type === 'bg') return (
    <div style={base}>
      <div style={{ ...img, inset: 0 }} />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 14px', gap: 5 }}>
        <div style={line('55%', 6)} />
        <div style={line('75%')} />
        <div style={line('45%')} />
      </div>
    </div>
  )
  if (type === 'inset_top') return (
    <div style={base}>
      <div style={{ ...img, top: 0, left: 0, right: 0, height: '44%' }} />
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '52%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 14px', gap: 4 }}>
        <div style={line('60%', 5)} />
        <div style={line('85%')} />
      </div>
    </div>
  )
  if (type === 'inset_right') return (
    <div style={{ ...base, display: 'flex' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 12px', gap: 4 }}>
        <div style={line('80%', 5)} />
        <div style={line('90%')} />
        <div style={line('65%')} />
      </div>
      <div style={{ width: '38%', background: 'var(--brand)', opacity: 0.35 }} />
    </div>
  )
  if (type === 'inner') return (
    <div style={{ ...base, display: 'flex', flexDirection: 'column', padding: 10, gap: 6 }}>
      <div style={line('45%', 5)} />
      <div style={{ flex: 1, borderRadius: 4, background: 'var(--brand)', opacity: 0.35 }} />
    </div>
  )
  if (type === 'zone') return (
    <div style={{ ...base, display: 'flex', flexDirection: 'column', padding: 10, gap: 6 }}>
      <div style={{ flex: 1, borderRadius: 4, background: 'var(--brand)', opacity: 0.35, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '0 14px' }}>
          <div style={line('70%', 5)} />
          <div style={line('50%')} />
        </div>
      </div>
    </div>
  )
  return null
}

const THEME_PRESETS = [
  { key: 'tech_blue',     label: '테크 블루',    primary: '#2563EB', dark: '#1A4C96' },
  { key: 'forest_green',  label: '포레스트 그린', primary: '#16A34A', dark: '#166534' },
  { key: 'sunset_orange', label: '썬셋 오렌지',  primary: '#EA580C', dark: '#9A3412' },
  { key: 'royal_violet',  label: '로열 바이올렛',primary: '#7C3AED', dark: '#4C1D95' },
  { key: 'golden_yellow', label: '골든 옐로',    primary: '#D97706', dark: '#92400E' },
  { key: 'slate',         label: '슬레이트',     primary: '#475569', dark: '#1E293B' },
] as const

const THEME_PRIMARY_PRESETS = THEME_PRESETS.map((t) => t.primary)

// ── 섹션 헤더 ─────────────────────────────────────────────────────────────
function SectionHead({ children }: { children: React.ReactNode }) {
  return (
    <h3 style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.12em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 12 }}>
      {children}
    </h3>
  )
}

// ── 컴포넌트 ──────────────────────────────────────────────────────────────
export default function RightPanel({
  jobId, activeCard, onImageUpdate, imageUploadRequested, onImageUploadHandled,
  currentThemePrimary, recommendedThemeKey, onThemeChange,
  bgColor, onBgColorChange,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [fontFamily, setFontFamily] = useState<'serif' | 'sans'>('serif')
  const [letterSpacing, setLs]      = useState(0)
  const [lineHeight, setLh]         = useState(1.6)
  const [dragOver, setDragOver]     = useState(false)
  const [openColorRow, setOpenColorRow] = useState<'bg' | 'theme' | null>(null)

  const slotMeta = activeCard ? getSlotMeta(activeCard.template_type) : null
  const hasSlot  = slotMeta?.type !== 'none'
  const imageUrl = activeCard?.image_url

  useEffect(() => {
    if (imageUploadRequested && hasSlot) {
      fileInputRef.current?.click()
      onImageUploadHandled?.()
    }
  }, [imageUploadRequested, hasSlot, onImageUploadHandled])

  function readFile(file: File) {
    const reader = new FileReader()
    reader.onload = () => onImageUpdate(reader.result as string)
    reader.readAsDataURL(file)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) readFile(file)
    e.target.value = ''
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file?.type.startsWith('image/')) readFile(file)
  }

  return (
    <aside
      className="flex flex-col h-full bg-canvas border-l border-surface-border overflow-hidden shrink-0 select-none"
      style={{ width: 280 }}
    >
      {/* ── 헤더 ── */}
      <header
        className="flex justify-between items-center border-b border-border-subtle shrink-0"
        style={{ padding: '20px 22px 14px' }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.025em', color: 'var(--ink)' }}>
          디자인 설정
        </h2>
        <div className="flex gap-2 text-ink-2">
          <button aria-label="Expand" className="hover:bg-forest-green-wash p-1 rounded transition-colors">
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>open_in_full</span>
          </button>
          <button aria-label="Close" className="hover:bg-forest-green-wash p-1 rounded transition-colors">
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>close</span>
          </button>
        </div>
      </header>

      {/* ── 스크롤 영역 ── */}
      <div className="flex-1 overflow-y-auto flex flex-col min-h-0" style={{ padding: '14px 22px', gap: 24 }}>

        {/* §1 — 색상 (아코디언) */}
        <section>
          <SectionHead>색상</SectionHead>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* 배경색 행 */}
            <div>
              <button
                onClick={() => setOpenColorRow((v) => v === 'bg' ? null : 'bg')}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '7px 10px', borderRadius: 8, border: '1px solid transparent',
                  background: openColorRow === 'bg' ? 'var(--canvas-subtle)' : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>배경</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 16, height: 16, borderRadius: 3, background: bgColor, border: '1px solid rgba(255,255,255,0.2)' }} />
                  <span style={{ fontSize: 11, color: 'var(--ink-3)', fontFamily: 'monospace' }}>{bgColor}</span>
                  <span style={{ fontSize: 10, color: 'var(--ink-3)' }}>{openColorRow === 'bg' ? '▴' : '▾'}</span>
                </div>
              </button>
              {openColorRow === 'bg' && (
                <div style={{ padding: '8px 10px 10px' }}>
                  <ColorPicker value={bgColor} onChange={onBgColorChange} />
                </div>
              )}
            </div>

            {/* 테마 강조색 행 */}
            <div>
              <button
                onClick={() => setOpenColorRow((v) => v === 'theme' ? null : 'theme')}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '7px 10px', borderRadius: 8, border: '1px solid transparent',
                  background: openColorRow === 'theme' ? 'var(--canvas-subtle)' : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>테마 강조</span>
                  {recommendedThemeKey && (
                    <span style={{ fontSize: 8, fontWeight: 700, background: '#16A34A', color: '#fff', padding: '1px 5px', borderRadius: 10 }}>
                      AI
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 16, height: 16, borderRadius: 3, background: currentThemePrimary ?? '#2563EB', border: '1px solid rgba(255,255,255,0.2)' }} />
                  <span style={{ fontSize: 11, color: 'var(--ink-3)', fontFamily: 'monospace' }}>{currentThemePrimary ?? '#2563EB'}</span>
                  <span style={{ fontSize: 10, color: 'var(--ink-3)' }}>{openColorRow === 'theme' ? '▴' : '▾'}</span>
                </div>
              </button>
              {openColorRow === 'theme' && (
                <div style={{ padding: '8px 10px 10px' }}>
                  <ColorPicker
                    value={currentThemePrimary ?? '#2563EB'}
                    onChange={(hex) => {
                      const [h, s, v] = hexToHsv(hex)
                      const dark = hsvToHex(h, s, v * 0.65)
                      onThemeChange({ primary: hex, dark })
                    }}
                    presets={THEME_PRIMARY_PRESETS}
                  />
                </div>
              )}
            </div>
          </div>
        </section>

        <div style={{ height: 1, background: 'var(--border-soft)' }} />

        {/* §2 — 이미지 */}
        <section>
          <SectionHead>이미지</SectionHead>

          {!hasSlot ? (
            /* 이미지 슬롯 없는 템플릿 */
            <div className="flex flex-col items-center gap-2" style={{ padding: '16px 0' }}>
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--canvas-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--ink-3)' }}>hide_image</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--ink-3)', textAlign: 'center', lineHeight: 1.6 }}>
                이 템플릿은<br />이미지 슬롯이 없습니다
              </p>
            </div>
          ) : (
            <>
              {/* 슬롯 위치 다이어그램 */}
              <SlotDiagram type={slotMeta!.type} />
              <p style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 6, marginBottom: 12, lineHeight: 1.5 }}>
                <strong style={{ color: 'var(--ink-2)' }}>{slotMeta!.label}</strong>
                {' '}— {slotMeta!.description}
              </p>

              {imageUrl ? (
                /* 이미지 있음: 썸네일 + 버튼 */
                <div>
                  <div style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', marginBottom: 8, border: '1px solid var(--border-subtle)' }}>
                    <img
                      src={imageUrl}
                      alt="카드 이미지"
                      style={{ width: '100%', height: 96, objectFit: 'cover', display: 'block' }}
                    />
                    <button
                      onClick={() => onImageUpdate(null)}
                      aria-label="이미지 제거"
                      style={{ position: 'absolute', top: 6, right: 6, width: 24, height: 24, borderRadius: '50%', background: 'rgba(0,0,0,0.55)', border: 'none', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 13 }}>close</span>
                    </button>
                  </div>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    style={{ width: '100%', height: 34, borderRadius: 8, border: '1px solid var(--border-soft)', background: 'var(--canvas-subtle)', fontSize: 12, fontWeight: 600, color: 'var(--ink-2)', cursor: 'pointer' }}
                  >
                    이미지 교체
                  </button>
                </div>
              ) : (
                /* 이미지 없음: 큰 드래그존 */
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click() }}
                  onDrop={handleDrop}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  style={{
                    borderRadius: 12, cursor: 'pointer', padding: '22px 16px',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                    border: `2px dashed ${dragOver ? 'var(--brand)' : 'var(--border-soft)'}`,
                    background: dragOver ? 'var(--brand-soft)' : 'transparent',
                    transition: 'all 0.15s',
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 30, color: dragOver ? 'var(--brand)' : 'var(--ink-3)' }}>
                    add_photo_alternate
                  </span>
                  <div style={{ textAlign: 'center' }}>
                    <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-2)', marginBottom: 2 }}>이미지 추가</p>
                    <p style={{ fontSize: 11, color: 'var(--ink-3)' }}>클릭 또는 드래그</p>
                  </div>
                </div>
              )}

              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
            </>
          )}
        </section>

        <div style={{ height: 1, background: 'var(--border-soft)' }} />

        {/* §3 — 타이포그래피 */}
        <section>
          <SectionHead>타이포그래피 스타일</SectionHead>

          {/* Serif / Sans 토글 */}
          <div
            className="flex bg-canvas-subtle border border-border-subtle"
            style={{ padding: 4, borderRadius: 10, marginBottom: 16 }}
          >
            {(['serif', 'sans'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFontFamily(f)}
                className={`flex-1 text-center transition-all ${
                  fontFamily === f
                    ? 'bg-canvas shadow-sm text-ink-1 font-semibold'
                    : 'text-ink-3 hover:text-ink-1'
                }`}
                style={{ paddingBlock: 6, borderRadius: 6, fontSize: 12, letterSpacing: '0.03em' }}
              >
                {f === 'serif' ? 'Serif' : 'Sans'}
              </button>
            ))}
          </div>

          {/* 슬라이더 */}
          <div className="flex flex-col" style={{ gap: 12 }}>
            {[
              { label: '자간 (Tracking)', val: letterSpacing, set: setLs,  min: -0.05, max: 0.1,  step: 0.01, fmt: (v: number) => `${v.toFixed(2)}em` },
              { label: '행간 (Leading)',  val: lineHeight,    set: setLh,  min: 1.2,   max: 2.0,   step: 0.1,  fmt: (v: number) => v.toFixed(1) },
            ].map(s => (
              <div key={s.label} className="flex flex-col" style={{ gap: 4 }}>
                <div className="flex justify-between">
                  <label style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.03em', color: 'var(--ink)' }}>{s.label}</label>
                  <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.03em', color: 'var(--ink-3)' }}>{s.fmt(s.val)}</span>
                </div>
                <input
                  type="range" min={s.min} max={s.max} step={s.step} value={s.val}
                  onChange={e => s.set(parseFloat(e.target.value))}
                  className="w-full h-1 rounded-lg appearance-none cursor-pointer accent-forest-green bg-canvas-muted"
                />
              </div>
            ))}
          </div>
        </section>


      </div>
    </aside>
  )
}
