'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { getCardPreviewHtml } from '@/lib/api'
import { getSlotType } from '@/lib/imageSlots'
import type { Card } from '@/types/editor'

function pad(n: number) { return String(n).padStart(2, '0') }

// ── 클라이언트 카드 HTML 빌더 (demo 모드) ──────────────────────────────────
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

const TEMPLATE_ABBR: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제', circle3: '3P',
  compare2: '비교', grid4: '4분', definition: '정의', flow: '흐름',
  data: '수치', showcase: '성과', closing: '마무리', brand: '브랜드',
}

// ── 썸네일 (실제 카드 iframe 미리보기) ───────────────────────────────────
function FilmThumb({ card, idx, total, isActive, onClick, jobId, isDemo, refreshTrigger }: {
  card: Card; idx: number; total: number; isActive: boolean; onClick: () => void
  jobId: string; isDemo?: boolean; refreshTrigger?: number
}) {
  const size = isActive ? 88 : 62
  const scale = size / CARD_SIZE
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [htmlContent, setHtmlContent] = useState<string | null>(null)

  useEffect(() => {
    if (!card) return
    if (isDemo) {
      setHtmlContent(buildCardHtml(card, idx, total))
      return
    }
    getCardPreviewHtml(jobId, card.card_num)
      .then(res => setHtmlContent(res.data))
      .catch(() => setHtmlContent(buildCardHtml(card, idx, total)))
  }, [card, idx, total, refreshTrigger, isDemo, jobId])

  useEffect(() => {
    const iframeEl = iframeRef.current
    if (!iframeEl || !htmlContent) return
    const doc = iframeEl.contentDocument
    if (!doc) return
    const cssLinks = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'))
      .map(l => `<link rel="stylesheet" href="${l.href}">`)
      .join('\n')
    doc.open()
    doc.write(`<!DOCTYPE html><html><head><meta charset="utf-8">${cssLinks}
      <style>html,body{margin:0;padding:0;width:${CARD_SIZE}px;height:${CARD_SIZE}px;overflow:hidden;background:white;}
      .preview-card{width:${CARD_SIZE}px;height:${CARD_SIZE}px;}</style>
    </head><body><div class="preview-card">${htmlContent}</div></body></html>`)
    doc.close()
  }, [htmlContent, size])

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
        {/* 실제 카드 축소 렌더링 */}
        <iframe
          ref={iframeRef}
          title={`카드 ${idx} 썸네일`}
          style={{ width: CARD_SIZE, height: CARD_SIZE, border: 'none', transform: `scale(${scale})`, transformOrigin: '0 0', display: 'block', pointerEvents: 'none' }}
          scrolling="no"
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
function IconEdit2() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3Z" />
    </svg>
  )
}
function IconDownload2() {
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

// ── 이미지 슬롯 오버레이 위치 ─────────────────────────────────────────────
const SLOT_OVERLAY: Record<string, { top: string; left: string; right: string; bottom: string }> = {
  bg:          { top: '0',   left: '0',   right: '0',   bottom: '0' },
  inset_top:   { top: '0',   left: '0',   right: '0',   bottom: '60%' },
  inset_right: { top: '0',   left: '62%', right: '0',   bottom: '0' },
  inner:       { top: '55%', left: '5%',  right: '5%',  bottom: '12%' },
}

function ImageSlotOverlay({
  slotType, imageUrl, onUploadRequest, scale,
}: {
  slotType: string; imageUrl?: string; onUploadRequest: () => void; scale: number
}) {
  const [hovered, setHovered] = useState(false)
  const pos = SLOT_OVERLAY[slotType]
  if (!pos) return null

  return (
    <div
      style={{ position: 'absolute', ...pos, zIndex: 20 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {imageUrl ? (
        <div className="relative w-full h-full group">
          {slotType === 'bg' && (
            <div
              className="absolute inset-0 rounded-lg overflow-hidden"
              style={{ backgroundImage: `url(${imageUrl})`, backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.45 }}
            />
          )}
          <div
            className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'}`}
            style={{ background: 'oklch(14% 0.04 152 / 0.40)', borderRadius: 8 }}
          >
            <button onClick={onUploadRequest} className="bg-white/90 text-ink-1 text-[12px] font-bold px-3 py-1.5 rounded-lg shadow-lg hover:bg-white transition-colors">
              이미지 교체
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={onUploadRequest}
          className="w-full h-full flex flex-col items-center justify-center gap-1.5 transition-all duration-200 rounded-lg"
          style={{
            borderWidth: Math.max(1, 2 * scale),
            borderStyle: 'dashed',
            borderColor: hovered ? 'oklch(38% 0.14 152)' : 'oklch(38% 0.14 152 / 0.4)',
            background: hovered ? 'oklch(38% 0.14 152 / 0.08)' : 'oklch(38% 0.14 152 / 0.03)',
          }}
        >
          <div
            className="rounded-full flex items-center justify-center"
            style={{
              width: Math.max(24, 32 * scale), height: Math.max(24, 32 * scale),
              background: hovered ? 'oklch(38% 0.14 152 / 0.15)' : 'oklch(38% 0.14 152 / 0.08)',
            }}
          >
            <svg width={Math.max(12, 16 * scale)} height={Math.max(12, 16 * scale)} viewBox="0 0 16 16" fill="none" style={{ color: 'oklch(38% 0.14 152)' }}>
              <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </div>
          {scale > 0.35 && (
            <span style={{ fontSize: Math.max(9, 11 * scale), color: 'oklch(38% 0.14 152)', fontWeight: 600 }}>이미지 추가</span>
          )}
        </button>
      )}
    </div>
  )
}

// ── Props ────────────────────────────────────────────────────────────────
interface Props {
  jobId: string
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  refreshTrigger?: number
  isDemo?: boolean
  onFieldFocus?: (field: string) => void
  onImageUploadRequest?: () => void
}

// ── 카드 크기 상수 ─────────────────────────────────────────────────────────
const CARD_SIZE = 1080
const PADDING   = 64

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function MidCanvas({
  jobId, cards, activeCardIdx, onSelectCard, refreshTrigger, isDemo, onFieldFocus, onImageUploadRequest,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const iframeRef    = useRef<HTMLIFrameElement>(null)
  const [scale, setScale] = useState(1)
  const [htmlContent, setHtmlContent] = useState<string | null>(null)

  const activeCard = cards[activeCardIdx]
  const cardNum    = activeCard?.card_num ?? activeCardIdx + 1
  const total      = cards.length
  const slotType   = activeCard ? getSlotType(activeCard.template_type) : null
  const imageUrl   = activeCard?.image_url

  // 컨테이너 크기 계산
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

  // 카드 HTML 로드
  useEffect(() => {
    if (!activeCard) return
    if (isDemo) {
      setHtmlContent(buildCardHtml(activeCard, cardNum, total))
      return
    }
    getCardPreviewHtml(jobId, activeCard.card_num).then(res => setHtmlContent(res.data)).catch(() => {
      setHtmlContent(buildCardHtml(activeCard, cardNum, total))
    })
  }, [activeCard, refreshTrigger, isDemo, jobId, cardNum, total])

  // iframe에 CSS 주입
  useEffect(() => {
    const iframeEl = iframeRef.current
    if (!iframeEl || !htmlContent) return
    const doc = iframeEl.contentDocument
    if (!doc) return

    const cssLinks = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'))
      .map(l => `<link rel="stylesheet" href="${l.href}">`)
      .join('\n')

    doc.open()
    doc.write(`<!DOCTYPE html><html><head><meta charset="utf-8">${cssLinks}
      <style>
        html,body{margin:0;padding:0;width:${CARD_SIZE}px;height:${CARD_SIZE}px;overflow:hidden;background:white;}
        .preview-card{width:${CARD_SIZE}px;height:${CARD_SIZE}px;}
      </style>
    </head><body><div class="preview-card">${htmlContent}</div></body></html>`)
    doc.close()
  }, [htmlContent])

  // 클릭→필드 포커스
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!activeCard || !onFieldFocus) return
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
    const relY = (e.clientY - rect.top) / rect.height
    const tmpl = activeCard.template_type
    const zones: { field: string; yMin: number; yMax: number }[] = (
      {
        cover:      [{field:'title',yMin:0.12,yMax:0.42},{field:'subtitle',yMin:0.42,yMax:0.62}],
        data:       [{field:'stat_main',yMin:0.12,yMax:0.46},{field:'stat_desc',yMin:0.46,yMax:0.70}],
        hook:       [{field:'title',yMin:0.12,yMax:0.55},{field:'body',yMin:0.55,yMax:0.80}],
        problem:    [{field:'section_title',yMin:0.08,yMax:0.28},{field:'body',yMin:0.28,yMax:0.78}],
        closing:    [{field:'section_title',yMin:0.22,yMax:0.48},{field:'body',yMin:0.48,yMax:0.74}],
        definition: [{field:'section_title',yMin:0.08,yMax:0.28},{field:'body',yMin:0.28,yMax:0.74}],
        flow:       [{field:'section_title',yMin:0.08,yMax:0.22},{field:'step1',yMin:0.22,yMax:0.38}],
      } as Record<string, typeof zones>
    )[tmpl] ?? []
    const hit = zones.find(z => relY >= z.yMin && relY <= z.yMax)
    if (hit) onFieldFocus(hit.field)
  }, [activeCard, onFieldFocus])

  const canvasSize = CARD_SIZE * scale

  return (
    <main className="flex-1 flex flex-col relative overflow-hidden bg-canvas-subtle min-h-0">

      {/* ── 메인 프리뷰 영역 ── */}
      <div ref={containerRef} className="flex-1 flex items-center justify-center relative px-6 py-4 min-h-0">

        {/* 이전 카드 버튼 */}
        <button
          onClick={() => onSelectCard(Math.max(0, activeCardIdx - 1))}
          disabled={activeCardIdx === 0}
          aria-label="이전 카드"
          className="absolute left-4 lg:left-8 w-10 h-10 bg-forest-green text-canvas rounded-[10px] flex items-center justify-center hover:bg-forest-green-deep disabled:opacity-30 disabled:cursor-not-allowed transition-colors shadow-md z-20 active:translate-y-px"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 24 }}>chevron_left</span>
        </button>

        {/* 카드 캔버스 — DESIGN_3.md 예외 shadow-md 적용 */}
        <div
          className="relative rounded-[14px] overflow-hidden shadow-md"
          style={{ width: canvasSize, height: canvasSize, flexShrink: 0 }}
          onClick={handleCanvasClick}
        >
          <iframe
            ref={iframeRef}
            title={`카드 ${pad(cardNum)} 미리보기`}
            style={{ width: CARD_SIZE, height: CARD_SIZE, border: 'none', transform: `scale(${scale})`, transformOrigin: '0 0', display: 'block', pointerEvents: 'none' }}
            scrolling="no"
          />
          {slotType && (
            <ImageSlotOverlay
              slotType={slotType}
              imageUrl={imageUrl}
              onUploadRequest={onImageUploadRequest ?? (() => {})}
              scale={scale}
            />
          )}
        </div>

        {/* 다음 카드 버튼 */}
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

        {/* Row 1: 카운터 | 플로팅 액션 | 여백 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', padding: '12px 22px 0', gap: 14 }}>

          {/* 카운터 + 타입 칩 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em', display: 'inline-flex', alignItems: 'baseline', gap: 5 }}>
              {pad(cardNum)}
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>/ {pad(total)}</span>
            </span>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--brand)', background: 'var(--brand-soft)', padding: '4px 10px', borderRadius: 999, whiteSpace: 'nowrap' }}>
              {TEMPLATE_ABBR[activeCard?.template_type] ?? activeCard?.template_type}
            </span>
          </div>

          {/* 플로팅 액션 패널 */}
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 2, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 4, boxShadow: '0 2px 8px rgba(15,27,22,.07), 0 1px 2px rgba(15,27,22,.04)' }}>
            <button type="button" className="bb-action" aria-label="편집"><IconEdit2 /></button>
            <button type="button" className="bb-action" aria-label="다운로드"><IconDownload2 /></button>
            <button type="button" className="bb-action" aria-label="복사"><IconCopy /></button>
            <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 3px' }} />
            <button type="button" className="bb-action danger" aria-label="삭제"><IconTrash /></button>
          </div>

          {/* 오른쪽 균형 여백 */}
          <div />
        </div>

        {/* Row 2: 갤러리 썸네일 스트립 */}
        <div style={{ padding: '14px 22px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, justifyContent: 'center', overflowX: 'auto', padding: '2px 0', scrollbarWidth: 'thin' }}>
            {cards.map((card, idx) => (
              <FilmThumb
                key={card.card_num}
                card={card}
                idx={card.card_num}
                total={total}
                isActive={idx === activeCardIdx}
                onClick={() => onSelectCard(idx)}
                jobId={jobId}
                isDemo={isDemo}
                refreshTrigger={refreshTrigger}
              />
            ))}
            {/* 카드 추가 */}
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
