'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { getCardPreviewHtml } from '@/lib/api'
import { getSlotType } from '@/lib/imageSlots'
import type { Card } from '@/types/editor'

function pad(n: number) { return String(n).padStart(2, '0') }

/* ── Client-side card HTML builder (demo mode) ── */
function buildCardHtml(card: Card, idx: number, total: number): string {
  const f: Record<string, string> = {}
  Object.entries(card.fields ?? {}).forEach(([k, v]) => { f[k] = v?.value ?? '' })

  const hdr = `<div class="cv-header">
    <span>${card.template_type}</span>
    <span class="cv-num">${pad(idx)} / ${pad(total)}</span>
  </div>`

  switch (card.template_type) {
    case 'cover':
      return `${hdr}<div class="cv-body">
        <p class="cv-cover-title">${f.title ?? ''}</p>
        <p class="cv-cover-sub">${f.subtitle ?? ''}</p>
        <p class="cv-cover-author">${f.institution ?? f.author ?? ''}</p>
      </div>`
    case 'problem':
      return `${hdr}<div class="cv-body">
        <h3 class="cv-section-title">${f.section_title ?? f.title ?? ''}</h3>
        <div class="cv-divider"></div>
        <p class="cv-body-text">${f.body ?? ''}</p>
      </div>`
    case 'data':
      return `${hdr}<div class="cv-body">
        <p class="cv-stat">${f.stat_main ?? f.stat ?? ''}</p>
        <p class="cv-desc">${f.stat_desc ?? f.description ?? ''}</p>
        ${(f.stat_sub || f.citation) ? `<span class="cv-citation">${f.stat_sub ?? f.citation}</span>` : ''}
      </div>`
    case 'flow': {
      const steps = ['step1','step2','step3','step4'].map(k => f[k]).filter(Boolean)
      return `${hdr}<div class="cv-body" style="justify-content:flex-start;padding-top:4cqw;">
        <h3 class="cv-section-title" style="font-size:5cqw;">${f.section_title ?? ''}</h3>
        <div class="cv-points">${steps.map(s => `<p class="cv-point">${s}</p>`).join('')}</div>
      </div>`
    }
    case 'closing':
      return `${hdr}<div class="cv-body" style="text-align:center;align-items:center;">
        <h3 class="cv-section-title">${f.section_title ?? ''}</h3>
        <div class="cv-divider"></div>
        <p class="cv-body-text">${f.body ?? ''}</p>
      </div>`
    default: {
      const entries = Object.entries(f).slice(0, 3)
      const title = f.section_title || f.title || card.template_type
      const rest = entries.filter(([k]) => !['section_title','title'].includes(k))
      return `${hdr}<div class="cv-body" style="justify-content:flex-start;">
        <h3 class="cv-section-title">${title}</h3>
        <div class="cv-divider"></div>
        ${rest.map(([, v]) => `<p class="cv-body-text">${v}</p>`).join('')}
      </div>`
    }
  }
}

/* ── 클릭 존 정의: 템플릿별 y축 범위로 어떤 필드인지 판단 ── */
type ClickZone = { field: string; yMin: number; yMax: number }
const TEMPLATE_CLICK_ZONES: Record<string, ClickZone[]> = {
  cover:      [{ field: 'title', yMin: 0.12, yMax: 0.42 }, { field: 'subtitle', yMin: 0.42, yMax: 0.62 }, { field: 'institution', yMin: 0.62, yMax: 0.78 }],
  data:       [{ field: 'stat_main', yMin: 0.12, yMax: 0.46 }, { field: 'stat_desc', yMin: 0.46, yMax: 0.70 }, { field: 'citation', yMin: 0.70, yMax: 0.85 }],
  hook:       [{ field: 'title', yMin: 0.12, yMax: 0.55 }, { field: 'body', yMin: 0.55, yMax: 0.80 }],
  problem:    [{ field: 'section_title', yMin: 0.08, yMax: 0.28 }, { field: 'body', yMin: 0.28, yMax: 0.78 }],
  closing:    [{ field: 'section_title', yMin: 0.22, yMax: 0.48 }, { field: 'body', yMin: 0.48, yMax: 0.74 }],
  definition: [{ field: 'section_title', yMin: 0.08, yMax: 0.28 }, { field: 'body', yMin: 0.28, yMax: 0.74 }],
  flow:       [{ field: 'section_title', yMin: 0.08, yMax: 0.22 }, { field: 'step1', yMin: 0.22, yMax: 0.38 }, { field: 'step2', yMin: 0.38, yMax: 0.54 }, { field: 'step3', yMin: 0.54, yMax: 0.70 }],
  showcase:   [{ field: 'section_title', yMin: 0.42, yMax: 0.58 }, { field: 'body', yMin: 0.58, yMax: 0.80 }],
}

/* ── 이미지 슬롯 오버레이 위치 ── */
const SLOT_OVERLAY: Record<string, { top: string; left: string; right: string; bottom: string }> = {
  bg:          { top: '0',   left: '0',   right: '0',   bottom: '0' },
  inset_top:   { top: '0',   left: '0',   right: '0',   bottom: '60%' },
  inset_right: { top: '0',   left: '62%', right: '0',   bottom: '0' },
  inner:       { top: '55%', left: '5%',  right: '5%',  bottom: '12%' },
}

const TEMPLATE_ABBR: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제', circle3: '3P',
  compare2: '비교', grid4: '4분', definition: '정의', flow: '흐름',
  data: '수치', showcase: '성과', closing: '마무리', brand: '브랜드',
}

/* ── 썸네일 ── */
function MiniThumb({ card, idx, isActive, onClick }: {
  card: Card; idx: number; isActive: boolean; onClick: () => void
}) {
  const abbr = TEMPLATE_ABBR[card.template_type] ?? card.template_type?.slice(0, 2)
  return (
    <button
      onClick={onClick}
      className={`ep-thumb ${isActive ? 'ep-thumb--active' : ''} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/60`}
      aria-label={`카드 ${idx}: ${abbr}`}
      title={`카드 ${idx} — ${abbr}`}
    >
      <div className="ep-thumb-header" />
      <div className="ep-thumb-body" style={{ flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 8, lineHeight: 1.2, opacity: 0.65, letterSpacing: '0.01em' }}>{abbr}</span>
        <span>{pad(idx)}</span>
      </div>
    </button>
  )
}

/* ── 이미지 슬롯 오버레이 ── */
function ImageSlotOverlay({
  slotType, imageUrl, onUploadRequest, scale,
}: {
  slotType: string
  imageUrl?: string
  onUploadRequest: () => void
  scale: number
}) {
  const [hovered, setHovered] = useState(false)
  const pos = SLOT_OVERLAY[slotType]
  if (!pos) return null

  const isFullBg = slotType === 'bg'

  return (
    <div
      style={{ position: 'absolute', ...pos, zIndex: 20 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {imageUrl ? (
        /* 이미지 있음: 호버시 교체 버튼 */
        <div className="relative w-full h-full group">
          {isFullBg && (
            <div
              className="absolute inset-0 rounded-lg overflow-hidden"
              style={{ backgroundImage: `url(${imageUrl})`, backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.45 }}
            />
          )}
          <div
            className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'}`}
            style={{ background: 'oklch(14% 0.04 152 / 0.40)', borderRadius: 8 }}
          >
            <button
              onClick={onUploadRequest}
              className="bg-white/90 text-ink text-[12px] font-bold px-3 py-1.5 rounded-lg shadow-lg hover:bg-white transition-colors"
            >
              이미지 교체
            </button>
          </div>
        </div>
      ) : (
        /* 이미지 없음: + 버튼 */
        <button
          onClick={onUploadRequest}
          className="w-full h-full flex flex-col items-center justify-center gap-1.5 transition-all duration-200 rounded-lg"
          style={{
            border: `${Math.max(1, 2 * scale)}px dashed`,
            borderColor: hovered ? 'oklch(38% 0.14 152)' : 'oklch(38% 0.14 152 / 0.4)',
            background: hovered ? 'oklch(38% 0.14 152 / 0.08)' : 'oklch(38% 0.14 152 / 0.03)',
          }}
        >
          <div
            className="rounded-full flex items-center justify-center transition-colors"
            style={{
              width: Math.max(24, 32 * scale),
              height: Math.max(24, 32 * scale),
              background: hovered ? 'oklch(38% 0.14 152 / 0.15)' : 'oklch(38% 0.14 152 / 0.08)',
            }}
          >
            <svg
              width={Math.max(12, 16 * scale)}
              height={Math.max(12, 16 * scale)}
              viewBox="0 0 16 16" fill="none"
              style={{ color: 'oklch(38% 0.14 152)' }}
            >
              <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
          </div>
          {scale > 0.35 && (
            <span style={{ fontSize: Math.max(9, 11 * scale), color: 'oklch(38% 0.14 152)', fontWeight: 600 }}>
              이미지 추가
            </span>
          )}
        </button>
      )}
    </div>
  )
}

/* ── Main ── */
const CARD_SIZE = 1080
const PADDING   = 64

interface Props {
  jobId: string
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  refreshTrigger: number
  isDemo?: boolean
  onFieldFocus?: (fieldKey: string) => void
  onImageUploadRequest?: () => void
}

export default function CardPreview({
  jobId, cards, activeCardIdx, onSelectCard, refreshTrigger,
  isDemo, onFieldFocus, onImageUploadRequest,
}: Props) {
  const activeCard = cards?.[activeCardIdx]
  const total      = cards?.length ?? 0
  const slotType   = getSlotType(activeCard?.template_type ?? '')

  const [iframeHtml, setIframeHtml] = useState('')
  const [loading,    setLoading]    = useState(false)
  const [scale,      setScale]      = useState(0.5)
  const areaRef = useRef<HTMLDivElement>(null)

  const recalcScale = useCallback(() => {
    if (!areaRef.current) return
    const { width, height } = areaRef.current.getBoundingClientRect()
    setScale(Math.max(Math.min((width - PADDING) / CARD_SIZE, (height - PADDING) / CARD_SIZE, 1), 0.1))
  }, [])

  useEffect(() => {
    recalcScale()
    const ro = new ResizeObserver(recalcScale)
    if (areaRef.current) ro.observe(areaRef.current)
    return () => ro.disconnect()
  }, [recalcScale])

  useEffect(() => {
    if (isDemo || !jobId || !activeCard) return
    let cancelled = false
    setLoading(true)
    getCardPreviewHtml(jobId, activeCard.card_num)
      .then(res => { if (!cancelled) setIframeHtml(res.data) })
      .catch(() => { if (!cancelled) setIframeHtml('') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [jobId, activeCard?.card_num, refreshTrigger, isDemo])

  /* ── 프리뷰 클릭 → 좌측 필드 포커스 ── */
  const handlePreviewClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!onFieldFocus || !activeCard) return
    const rect = e.currentTarget.getBoundingClientRect()
    const yFrac = (e.clientY - rect.top) / rect.height

    const zones = TEMPLATE_CLICK_ZONES[activeCard.template_type]
    if (!zones) return

    const zone = zones.find(z => yFrac >= z.yMin && yFrac <= z.yMax)
    if (!zone) return

    // 해당 필드가 실제로 존재하면 포커스
    const fieldExists = activeCard.fields && zone.field in activeCard.fields
    if (fieldExists) onFieldFocus(zone.field)
  }, [onFieldFocus, activeCard])

  const canGoPrev = activeCardIdx > 0
  const canGoNext = activeCardIdx < total - 1

  return (
    <div className="flex-1 flex flex-col bg-surface-subtle overflow-hidden">

      {/* 썸네일 스트립 */}
      <div
        className="flex items-center gap-1.5 px-4 py-2.5 bg-surface border-b border-surface-border overflow-x-auto shrink-0"
        style={{ maskImage: 'linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%)' }}
      >
        {cards?.map((card, idx) => (
          <MiniThumb
            key={card.card_num}
            card={card}
            idx={card.card_num}
            isActive={idx === activeCardIdx}
            onClick={() => onSelectCard(idx)}
          />
        ))}
      </div>

      {/* 프리뷰 영역 */}
      <div ref={areaRef} className="flex-1 flex items-center justify-center p-6 overflow-hidden relative">
        {isDemo ? (
          /* Demo: DOM 렌더링 */
          <div className="preview-card-wrap relative">
            <div
              className="preview-card"
              dangerouslySetInnerHTML={{
                __html: activeCard ? buildCardHtml(activeCard, activeCard.card_num, total) : ''
              }}
            />
          </div>
        ) : (
          /* Live: iframe */
          <div
            className="relative rounded-xl shadow-modal overflow-hidden shrink-0"
            style={{ width: CARD_SIZE * scale, height: CARD_SIZE * scale }}
            role="region"
            aria-label="카드 미리보기"
          >
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-surface-subtle z-10">
                <div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {/* iframe */}
            {iframeHtml ? (
              <iframe
                srcDoc={iframeHtml}
                title="카드 미리보기"
                sandbox="allow-same-origin"
                scrolling="no"
                style={{
                  width: CARD_SIZE, height: CARD_SIZE,
                  border: 'none',
                  display: loading ? 'none' : 'block',
                  transform: `scale(${scale})`,
                  transformOrigin: 'top left',
                  background: '#fff',
                }}
              />
            ) : !loading && (
              <div className="w-full h-full flex items-center justify-center text-[13px] text-ink-muted bg-white">
                미리보기 없음
              </div>
            )}

            {/* 클릭 → 필드 포커스 오버레이 (iframe 위) */}
            {!loading && iframeHtml && onFieldFocus && (
              <div
                role="button"
                tabIndex={0}
                className="absolute inset-0 cursor-pointer z-10"
                style={{ background: 'transparent' }}
                onClick={handlePreviewClick}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    const zones = TEMPLATE_CLICK_ZONES[activeCard?.template_type ?? '']
                    if (zones?.[0] && onFieldFocus) {
                      const fieldExists = activeCard?.fields && zones[0].field in activeCard.fields
                      if (fieldExists) onFieldFocus(zones[0].field)
                    }
                  }
                }}
                aria-label="카드 프리뷰 — 클릭하여 해당 필드로 이동"
                title="클릭하면 해당 필드로 이동합니다"
              />
            )}

            {/* 이미지 슬롯 오버레이 */}
            {!loading && slotType !== 'none' && onImageUploadRequest && (
              <ImageSlotOverlay
                slotType={slotType}
                imageUrl={activeCard?.image_url}
                onUploadRequest={onImageUploadRequest}
                scale={scale}
              />
            )}
          </div>
        )}
      </div>

      {/* 하단 네비게이션 */}
      <div className="px-4 py-3 bg-surface border-t border-surface-border flex items-center justify-between shrink-0">
        <button
          onClick={() => canGoPrev && onSelectCard(activeCardIdx - 1)}
          disabled={!canGoPrev}
          aria-label="이전 카드"
          className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-surface-subtle disabled:opacity-30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/40"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        <div className="flex items-center gap-3">
          <span className="text-[12px] font-semibold text-ink-muted tabular-nums">
            {activeCardIdx + 1} / {total}
          </span>
          {activeCard && (
            <span className="ep-template-badge">{activeCard.template_type}</span>
          )}
          {!loading && onFieldFocus && (
            <span className="hidden lg:inline text-[9px] text-ink-disabled">
              클릭으로 필드 이동
            </span>
          )}
        </div>

        <button
          onClick={() => canGoNext && onSelectCard(activeCardIdx + 1)}
          disabled={!canGoNext}
          aria-label="다음 카드"
          className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-surface-subtle disabled:opacity-30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/40"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
