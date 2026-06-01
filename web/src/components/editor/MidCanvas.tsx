'use client'

// MidCanvas — 카드 미리보기 + 네비게이션.
// Phase 3: iframe 제거, React CardRenderer 직접 호스트.
// 현재 mode='render' (view-only). Phase 4에서 mode='edit'으로 전환.

import { useCallback, useEffect, useRef, useState } from 'react'
import CardRenderer from '@/components/cards/CardRenderer'
import type { Card, CardTheme } from '@/types/editor'

const CARD_SIZE = 1080
const PADDING   = 64
const DEFAULT_THEME: CardTheme = { primary: '#2563EB', dark: '#1A4C96' }

const TEMPLATE_ABBR: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제', circle3: '3P',
  compare2: '비교', grid4: '4분', definition: '정의', flow: '흐름',
  data: '수치', showcase: '성과', closing: '마무리', brand: '브랜드',
}

function pad(n: number) { return String(n).padStart(2, '0') }

// ── Props ────────────────────────────────────────────────────────────────
interface Props {
  jobId: string
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  theme?: CardTheme
  isDemo?: boolean
  focusedField?: string | null
  onFieldFocus?: (field: string) => void
  onFieldChange?: (fieldKey: string, value: string) => void
  onImageUploadRequest?: () => void
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function MidCanvas({
  cards, activeCardIdx, onSelectCard, theme, focusedField,
  onFieldFocus, onFieldChange, onImageUploadRequest,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(0.5)

  const activeCard = cards[activeCardIdx]
  const cardNum    = activeCard?.card_num ?? activeCardIdx + 1
  const total      = cards.length
  const effectiveTheme = theme ?? DEFAULT_THEME

  // 컨테이너 크기에 맞춰 scale 계산
  const computeScale = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const { width, height } = el.getBoundingClientRect()
    const avail = Math.min(width - PADDING * 2, height - PADDING * 2)
    setScale(Math.max(0.2, avail / CARD_SIZE))
  }, [])

  useEffect(() => {
    computeScale()
    const ro = new ResizeObserver(computeScale)
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [computeScale])

  if (!activeCard) {
    return (
      <main className="flex-1 flex items-center justify-center bg-canvas-subtle">
        <div className="text-ink-3 text-sm">카드가 없습니다</div>
      </main>
    )
  }

  return (
    <main className="flex-1 flex flex-col relative overflow-hidden bg-canvas-subtle min-h-0">
      {/* ── 메인 프리뷰 영역 ── */}
      <div ref={containerRef} className="flex-1 flex items-center justify-center relative px-6 py-4 min-h-0">
        {/* 이전 카드 */}
        <button
          onClick={() => onSelectCard(Math.max(0, activeCardIdx - 1))}
          disabled={activeCardIdx === 0}
          aria-label="이전 카드"
          className="absolute left-4 lg:left-8 w-10 h-10 bg-forest-green text-canvas rounded-[10px] flex items-center justify-center hover:bg-forest-green-deep disabled:opacity-30 disabled:cursor-not-allowed transition-colors shadow-md z-20 active:translate-y-px"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 24 }}>chevron_left</span>
        </button>

        {/* 카드 캔버스 */}
        <div
          className="relative rounded-[14px] overflow-hidden shadow-md"
          style={{ flexShrink: 0 }}
        >
          <CardRenderer
            card={activeCard}
            theme={effectiveTheme}
            mode="edit"
            scale={scale}
            focusedField={focusedField}
            onFieldFocus={onFieldFocus}
            onFieldChange={onFieldChange}
            onImageRequest={onImageUploadRequest ? () => onImageUploadRequest() : undefined}
          />
        </div>

        {/* 다음 카드 */}
        <button
          onClick={() => onSelectCard(Math.min(cards.length - 1, activeCardIdx + 1))}
          disabled={activeCardIdx === cards.length - 1}
          aria-label="다음 카드"
          className="absolute right-4 lg:right-8 w-10 h-10 bg-forest-green text-canvas rounded-[10px] flex items-center justify-center hover:bg-forest-green-deep disabled:opacity-30 disabled:cursor-not-allowed transition-colors shadow-md z-20 active:translate-y-px"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 24 }}>chevron_right</span>
        </button>
      </div>

      {/* ── 하단 바 ── */}
      <div style={{ background: 'var(--surface)', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
        {/* Row 1: 카운터 + 액션 패널 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', padding: '12px 22px 0', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em', display: 'inline-flex', alignItems: 'baseline', gap: 5 }}>
              {pad(cardNum)}
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>/ {pad(total)}</span>
            </span>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--brand)', background: 'var(--brand-soft)', padding: '4px 10px', borderRadius: 999, whiteSpace: 'nowrap' }}>
              {TEMPLATE_ABBR[activeCard.template_type] ?? activeCard.template_type}
            </span>
          </div>

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 2, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 4, boxShadow: '0 2px 8px rgba(15,27,22,.07), 0 1px 2px rgba(15,27,22,.04)' }}>
            <button type="button" className="bb-action" aria-label="편집"><IconEdit /></button>
            <button type="button" className="bb-action" aria-label="다운로드"><IconDownload /></button>
            <button type="button" className="bb-action" aria-label="복사"><IconCopy /></button>
            <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 3px' }} />
            <button type="button" className="bb-action danger" aria-label="삭제"><IconTrash /></button>
          </div>

          <div />
        </div>

        {/* Row 2: 썸네일 스트립 (Phase 6에서 LeftPanel로 이전 예정) */}
        <div style={{ padding: '14px 22px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, justifyContent: 'center', overflowX: 'auto', padding: '2px 0', scrollbarWidth: 'thin' }}>
            {cards.map((card, idx) => (
              <FilmThumb
                key={card.card_num}
                card={card}
                theme={effectiveTheme}
                idx={card.card_num}
                isActive={idx === activeCardIdx}
                onClick={() => onSelectCard(idx)}
              />
            ))}
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                type="button"
                aria-label="카드 추가"
                className="bb-add-btn"
                style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 62, height: 62, border: '1.5px dashed var(--border)', borderRadius: 12, background: 'var(--surface-mid)', color: 'var(--ink-3)', cursor: 'pointer', transition: 'border-color 130ms ease, color 130ms ease, background-color 130ms ease' }}
              >
                <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

// ── 썸네일 (React 카드 thumbnail 모드) ────────────────────────────────────
function FilmThumb({ card, theme, idx, isActive, onClick }: {
  card: Card; theme: CardTheme; idx: number; isActive: boolean; onClick: () => void
}) {
  const size = isActive ? 88 : 62
  const scale = size / CARD_SIZE

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
      <button
        onClick={onClick}
        aria-label={`카드 ${idx}`}
        className="bb-thumb-btn"
        style={{
          position: 'relative',
          width: size,
          height: size,
          flexShrink: 0,
          border: isActive ? '2px solid var(--brand)' : '1.5px solid var(--border)',
          borderRadius: 9,
          background: 'var(--surface)',
          cursor: 'pointer',
          padding: 0,
          overflow: 'hidden',
          transition: 'border-color 130ms ease, box-shadow 130ms ease, transform 90ms ease',
          boxShadow: isActive
            ? '0 0 0 3px var(--brand-soft), 0 6px 16px -6px oklch(38% 0.14 152 / 0.35)'
            : undefined,
        }}
      >
        <CardRenderer
          card={card}
          theme={theme}
          mode="thumbnail"
          scale={scale}
        />
        {/* 상단 브랜드 밴드 오버레이 */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 5, background: 'var(--brand)', opacity: isActive ? 1 : 0.85, pointerEvents: 'none' }} />
        {/* 카드 번호 (우상단) */}
        <div style={{ position: 'absolute', top: 6, right: 6, fontSize: 8.5, fontWeight: 800, color: 'var(--ink-3)', fontVariantNumeric: 'tabular-nums', letterSpacing: '0.02em', lineHeight: 1, pointerEvents: 'none' }}>
          {pad(idx)}
        </div>
      </button>
    </div>
  )
}

// ── 아이콘 ────────────────────────────────────────────────────────────────
function IconEdit() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3Z" />
    </svg>
  )
}
function IconDownload() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}
function IconCopy() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}
function IconTrash() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" /><path d="M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  )
}
