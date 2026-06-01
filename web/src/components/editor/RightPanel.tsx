'use client'

import { useRef, useEffect, useState } from 'react'
import { getCardImageUrl } from '@/lib/api'
import { getSlotMeta } from '@/lib/imageSlots'
import type { Card, CardTheme } from '@/types/editor'

interface Props {
  jobId: string
  activeCard?: Card
  onImageUpdate: (imageUrl: string | null) => void
  imageUploadRequested?: boolean
  onImageUploadHandled?: () => void
  currentThemePrimary?: string
  recommendedThemeKey?: string
  onThemeChange: (theme: CardTheme) => void
}

const IMAGE_SLOTS = [
  { icon: 'splitscreen',    title: '전체 배경',  type: 'bg' },
  { icon: 'web_asset',      title: '상단 인셋',  type: 'inset_top' },
  { icon: 'view_sidebar',   title: '우측 인셋',  type: 'inset_right' },
  { icon: 'call_to_action', title: '텍스트 하단', type: 'inner' },
] as const

const THEME_PRESETS = [
  { key: 'tech_blue',     label: '테크 블루',    primary: '#2563EB', dark: '#1A4C96' },
  { key: 'forest_green',  label: '포레스트 그린', primary: '#16A34A', dark: '#166534' },
  { key: 'sunset_orange', label: '썬셋 오렌지',  primary: '#EA580C', dark: '#9A3412' },
  { key: 'royal_violet',  label: '로열 바이올렛',primary: '#7C3AED', dark: '#4C1D95' },
  { key: 'golden_yellow', label: '골든 옐로',    primary: '#D97706', dark: '#92400E' },
  { key: 'slate',         label: '슬레이트',     primary: '#475569', dark: '#1E293B' },
] as const

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
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [fontFamily, setFontFamily]   = useState<'serif' | 'sans'>('serif')
  const [letterSpacing, setLs]        = useState(0)
  const [lineHeight, setLh]           = useState(1.6)
  const [uploading, setUploading]     = useState(false)

  const slotMeta     = activeCard ? getSlotMeta(activeCard.template_type) : null
  const hasSlot      = !!slotMeta
  const imageUrl     = activeCard?.image_url
  const activeSlot   = slotMeta?.type ?? 'inset_top'

  useEffect(() => {
    if (imageUploadRequested && hasSlot) {
      fileInputRef.current?.click()
      onImageUploadHandled?.()
    }
  }, [imageUploadRequested, hasSlot, onImageUploadHandled])

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !activeCard) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`/api/jobs/${jobId}/cards/${activeCard.card_num}/image`, { method: 'POST', body: fd })
      if (res.ok) { const { url } = await res.json(); onImageUpdate(url) }
    } finally { setUploading(false); e.target.value = '' }
  }

  async function handleRemoveImage() {
    if (!activeCard) return
    try {
      await fetch(`/api/jobs/${jobId}/cards/${activeCard.card_num}/image`, { method: 'DELETE' })
      onImageUpdate(null)
    } catch {}
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

        {/* §1 — 테마 색상 */}
        <section>
          <SectionHead>테마 색상</SectionHead>
          <div className="grid grid-cols-3" style={{ gap: 8 }}>
            {THEME_PRESETS.map(t => {
              const isActive = currentThemePrimary === t.primary
              const isRecommended = recommendedThemeKey === t.key
              return (
                <button
                  key={t.key}
                  aria-label={t.label}
                  onClick={() => onThemeChange({ primary: t.primary, dark: t.dark })}
                  className={`relative flex flex-col items-center gap-1 transition-all ${
                    isActive
                      ? 'border-2 border-forest-green bg-forest-green-wash'
                      : 'border border-surface-border bg-surface-bright hover:bg-forest-green-ghost'
                  }`}
                  style={{ padding: '8px 4px', borderRadius: 10 }}
                >
                  <div className="w-8 h-8 rounded-full" style={{ background: t.primary }} />
                  <span style={{
                    fontSize: 10, fontWeight: 600, color: 'var(--ink)',
                    lineHeight: 1.2, textAlign: 'center',
                  }}>
                    {t.label}
                  </span>
                  {isRecommended && (
                    <span
                      className="absolute -top-1.5 -right-1.5 text-[8px] font-bold px-1 rounded-full"
                      style={{ background: '#16A34A', color: '#fff', lineHeight: 1.6 }}
                    >
                      AI
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </section>

        <div style={{ height: 1, background: 'var(--border-soft)' }} />

        {/* §2 — 이미지 슬롯 */}
        <section>
          <div className="flex justify-between items-center" style={{ marginBottom: 12 }}>
            <SectionHead>이미지 슬롯</SectionHead>
          </div>

          {/* 레이아웃 버튼 4개 */}
          <div className="flex" style={{ gap: 8, marginBottom: 16 }}>
            {IMAGE_SLOTS.map(slot => {
              const isActive = hasSlot && activeSlot === slot.type
              return (
                <button
                  key={slot.type}
                  className={`flex-1 flex items-center justify-center transition-colors ${
                    isActive
                      ? 'border-2 border-forest-green bg-forest-green-wash'
                      : 'border border-surface-border bg-surface-bright hover:bg-forest-green-ghost'
                  }`}
                  style={{ height: 40, borderRadius: 10 }}
                  title={slot.title}
                >
                  <span
                    className={`material-symbols-outlined ${isActive ? 'text-forest-green' : 'text-ink-3'}`}
                    style={{ fontSize: 20 }}
                  >
                    {slot.icon}
                  </span>
                </button>
              )
            })}
          </div>

          {/* 현재 이미지 미리보기 */}
          {imageUrl && (
            <div className="relative mb-3 rounded-lg overflow-hidden border border-surface-border">
              <img
                src={getCardImageUrl(jobId, activeCard!.card_num)}
                alt="카드 이미지"
                className="w-full object-cover"
                style={{ height: 80 }}
              />
              <button
                onClick={handleRemoveImage}
                aria-label="이미지 제거"
                className="absolute top-1 right-1 w-6 h-6 bg-canvas/90 rounded-full flex items-center justify-center text-risk-critical hover:bg-canvas transition-colors"
              >
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>delete</span>
              </button>
            </div>
          )}

          {/* 업로드 버튼 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-wait transition-colors"
            style={{
              height: 36, borderRadius: 10, fontSize: 12, fontWeight: 600,
              letterSpacing: '0.03em', textTransform: 'uppercase',
              border: '1px solid var(--brand)', color: 'var(--brand)',
              background: 'transparent', cursor: 'pointer',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand-soft)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>upload_file</span>
            {uploading ? '업로드 중...' : '이미지 업로드'}
          </button>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
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
