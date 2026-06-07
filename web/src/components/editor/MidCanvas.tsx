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
  cover_v2: '표지', statement: '진술', feature: '혁신', process_v2: '과정',
  bigstat_compare: '성능', reasons: '근거', grid_v2: '응용', closing_v2: '마무리',
}

function pad(n: number) { return String(n).padStart(2, '0') }

// ── Props ────────────────────────────────────────────────────────────────
interface Props {
  jobId: string
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  theme?: CardTheme
  bgColor?: string
  isDemo?: boolean
  focusedField?: string | null
  onFieldFocus?: (field: string) => void
  onFieldChange?: (fieldKey: string, value: string) => void
  onImageUploadRequest?: () => void
  onFocalChange?: (focal: { x: number; y: number }) => void
  onFitChange?: (fit: 'cover' | 'contain') => void
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function MidCanvas({
  cards, activeCardIdx, onSelectCard, theme, bgColor, focusedField,
  onFieldFocus, onFieldChange, onImageUploadRequest, onFocalChange, onFitChange,
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
            bgColor={bgColor}
            mode="edit"
            scale={scale}
            focusedField={focusedField}
            onFieldFocus={onFieldFocus}
            onFieldChange={onFieldChange}
            onImageRequest={onImageUploadRequest ? () => onImageUploadRequest() : undefined}
            onFocalChange={onFocalChange}
            onFitChange={onFitChange}
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

      {/* ── 하단 바: 카운터 + 액션 패널 (썸네일 strip은 LeftPanel로 이전) ── */}
      <div style={{ background: 'var(--surface)', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', padding: '12px 22px', gap: 14 }}>
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
      </div>
    </main>
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
