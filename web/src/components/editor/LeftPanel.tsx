'use client'

// LeftPanel — 카드 네비게이터 (Phase 6 재작성).
//
// 기존: form 기반 필드 편집기.
// 신규: 12개 카드의 live 썸네일 strip + risk 배지. 필드 편집은 캔버스 + FactDrawer로 이동.

import { memo, useEffect, useRef } from 'react'
import CardRenderer from '@/components/cards/CardRenderer'
import type { Card, CardTheme, RiskLevel } from '@/types/editor'

const TEMPLATE_LABELS: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제', circle3: '3P',
  compare2: '비교', grid4: '4분', definition: '정의', flow: '흐름',
  data: '수치', showcase: '성과', closing: '마무리', brand: '브랜드',
}

const DEFAULT_THEME: CardTheme = { primary: '#2563EB', dark: '#1A4C96' }

function pad(n: number) { return String(n).padStart(2, '0') }

type RiskStatus = 'crit' | 'warn' | 'ok'

function getCardRiskStatus(card: Card): RiskStatus {
  const fields = card.fields ?? {}
  const risks = Object.values(fields).map((f) => f?.risk_level).filter(Boolean) as RiskLevel[]
  if (risks.includes('CRITICAL')) return 'crit'
  if (risks.some((r) => r === 'HIGH' || r === 'MEDIUM')) return 'warn'
  return 'ok'
}

// ── Props ────────────────────────────────────────────────────────────────
interface Props {
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  theme?: CardTheme
  bgColor?: string
}

// ── 메인 ─────────────────────────────────────────────────────────────────
export default function LeftPanel({ cards, activeCardIdx, onSelectCard, theme, bgColor }: Props) {
  const effectiveTheme = theme ?? DEFAULT_THEME
  const total = cards.length
  const criticalCount = cards.filter((c) => getCardRiskStatus(c) === 'crit').length

  return (
    <aside
      className="flex flex-col h-full bg-canvas border-r border-surface-border overflow-hidden shrink-0 select-none"
      style={{ width: 280 }}
    >
      {/* 헤더 */}
      <header
        className="flex justify-between items-center border-b border-border-subtle shrink-0"
        style={{ padding: '20px 22px 14px' }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.025em', color: 'var(--ink)' }}>
          카드 <span style={{ color: 'var(--ink-3)', fontWeight: 600 }}>({total})</span>
        </h2>
        <button
          aria-label="카드 추가"
          disabled
          title="준비 중"
          className="p-1 rounded"
          style={{ color: 'var(--ink-3)', opacity: 0.4, cursor: 'not-allowed' }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>add</span>
        </button>
      </header>

      {/* 썸네일 strip */}
      <div
        className="flex-1 overflow-y-auto min-h-0"
        style={{ padding: '14px 16px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}
      >
        {cards.map((card, idx) => (
          <ThumbItem
            key={card.card_num}
            card={card}
            theme={effectiveTheme}
            bgColor={bgColor}
            idx={idx}
            isActive={idx === activeCardIdx}
            onClick={() => onSelectCard(idx)}
          />
        ))}
      </div>

      {/* 푸터: 진행 + CRITICAL 카운트 */}
      <footer
        className="border-t border-border-subtle shrink-0"
        style={{ padding: '12px 18px 14px' }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
            검토 진행
          </span>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>
            {pad(activeCardIdx + 1)} / {pad(total)}
          </span>
        </div>
        <div style={{
          width: '100%', height: 3,
          background: 'var(--surface-mid, #f0f0f0)',
          borderRadius: 2, overflow: 'hidden',
        }}>
          <div style={{
            width: total > 0 ? `${((activeCardIdx + 1) / total) * 100}%` : '0%',
            height: '100%',
            background: 'var(--brand, #16A34A)',
            transition: 'width 200ms ease',
          }} />
        </div>
        {criticalCount > 0 && (
          <div style={{
            marginTop: 10,
            display: 'inline-flex', alignItems: 'center', gap: 6,
            fontSize: 11, fontWeight: 700,
            color: '#991B1B', background: '#FEE2E2',
            padding: '4px 10px', borderRadius: 999,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#DC2626' }} />
            CRITICAL {criticalCount}장
          </div>
        )}
      </footer>
    </aside>
  )
}

// ── 썸네일 아이템 ─────────────────────────────────────────────────────────
const ThumbItem = memo(function ThumbItem({
  card, theme, bgColor, idx, isActive, onClick,
}: {
  card: Card
  theme: CardTheme
  bgColor?: string
  idx: number
  isActive: boolean
  onClick: () => void
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const riskStatus = getCardRiskStatus(card)

  // active 변경 시 스크롤
  useEffect(() => {
    if (isActive && wrapRef.current) {
      wrapRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [isActive])

  const thumbSize = 200       // 표시 크기 (px)
  const scale = thumbSize / 1080

  return (
    <div ref={wrapRef} style={{ flexShrink: 0, contain: 'layout style paint' }}>
      <button
        type="button"
        onClick={onClick}
        aria-label={`카드 ${idx + 1}`}
        style={{
          width: '100%',
          padding: 0,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}
      >
        {/* 썸네일 박스 */}
        <div style={{
          position: 'relative',
          width: thumbSize,
          height: thumbSize,
          alignSelf: 'center',
          borderRadius: 10,
          overflow: 'hidden',
          border: isActive ? '2px solid var(--brand, #16A34A)' : '1.5px solid var(--border)',
          boxShadow: isActive
            ? '0 0 0 3px var(--brand-soft, rgba(22,163,74,0.18)), 0 6px 16px -6px rgba(22,163,74,0.30)'
            : '0 1px 3px rgba(0,0,0,0.05)',
          transition: 'border-color 130ms ease, box-shadow 130ms ease',
          background: '#fafafa',
        }}>
          <CardRenderer
            card={card}
            theme={theme}
            bgColor={bgColor}
            mode="thumbnail"
            scale={scale}
          />
          {/* risk 배지 (top-right) */}
          {riskStatus !== 'ok' && (
            <div style={{
              position: 'absolute', top: 6, right: 6,
              width: 14, height: 14, borderRadius: '50%',
              background: riskStatus === 'crit' ? '#DC2626' : '#EA580C',
              border: '2px solid #fff',
              boxShadow: '0 0 0 1px rgba(0,0,0,0.1)',
            }} />
          )}
          {/* 카드 번호 (top-left) */}
          <div style={{
            position: 'absolute', top: 6, left: 6,
            background: 'rgba(255,255,255,0.92)',
            color: 'var(--ink)',
            fontSize: 10, fontWeight: 800,
            padding: '2px 6px', borderRadius: 6,
            fontVariantNumeric: 'tabular-nums',
            letterSpacing: '0.02em',
          }}>
            {pad(card.card_num)}
          </div>
        </div>

        {/* 라벨 */}
        <div style={{
          fontSize: 11, fontWeight: 600,
          color: isActive ? 'var(--ink)' : 'var(--ink-2)',
          textAlign: 'center',
        }}>
          {TEMPLATE_LABELS[card.template_type] ?? card.template_type}
        </div>
      </button>
    </div>
  )
})
