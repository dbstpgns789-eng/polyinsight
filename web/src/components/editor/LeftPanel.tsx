'use client'

import { useEffect, useRef } from 'react'
import type { FieldValue, Card } from '@/types/editor'

// ── 상수 ──────────────────────────────────────────────────────────────────
const TEMPLATE_LABELS: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제제기', circle3: '3포인트',
  compare2: '비교', grid4: '4분면', definition: '정의', flow: '흐름도',
  data: '데이터', showcase: '성과', closing: '마무리', brand: '브랜딩',
}

const FIELD_LABELS: Record<string, string> = {
  title: '제목', subtitle: '부제목', body: '본문', description: '설명',
  section_title: '섹션 제목', stat_main: '핵심 수치', stat_desc: '수치 설명',
  stat_sub: '보조 수치', citation: '출처', institution: '기관', author: '저자',
  step1: '단계 1', step2: '단계 2', step3: '단계 3', step4: '단계 4',
}

function pad(n: number) { return String(n).padStart(2, '0') }

function getCardTitle(card: Card): string {
  const f = card.fields ?? {}
  return f.title?.value || f.section_title?.value || TEMPLATE_LABELS[card.template_type] || card.template_type
}

// ── 상태 계산 ─────────────────────────────────────────────────────────────
type DotStatus = 'crit' | 'warn' | 'ok'

function getCardStatus(card: Card): DotStatus {
  const fields = card.fields ?? {}
  if (Object.values(fields).some(f => f?.risk_level === 'CRITICAL')) return 'crit'
  if (Object.values(fields).some(f => f?.risk_level === 'HIGH' || f?.risk_level === 'MEDIUM')) return 'warn'
  return 'ok'
}

function getFieldStatus(fv: FieldValue): 'ok' | 'warn' | 'crit' | null {
  const risk = fv?.risk_level
  if (risk === 'CRITICAL') return 'crit'
  if (risk === 'HIGH' || risk === 'MEDIUM') return 'warn'
  if (fv?.confidence === 'high') return 'ok'
  return null
}

const STATUS_LABEL: Record<string, string> = { ok: '확인됨', warn: '검토 권장', crit: '불일치' }

// ── Props ────────────────────────────────────────────────────────────────
interface Props {
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  onFieldChange: (fieldKey: string, value: string) => void
  onConfirmRisk: (fieldKey: string) => void
  focusedField?: string | null
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function LeftPanel({
  cards, activeCardIdx, onSelectCard, onFieldChange, focusedField,
}: Props) {
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})

  useEffect(() => {
    if (!focusedField) return
    const el = fieldRefs.current[focusedField]
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [focusedField])

  if (!cards?.length) return (
    <aside
      className="flex items-center justify-center h-full bg-canvas border-r shrink-0 text-[12px]"
      style={{ width: 320, borderColor: 'var(--border)', color: 'var(--ink-3)' }}
    >
      카드 데이터 없음
    </aside>
  )

  const activeCard = cards[activeCardIdx]
  const critCount = cards.filter(c =>
    Object.values(c.fields ?? {}).some(f => f?.risk_level === 'CRITICAL')
  ).length

  return (
    <aside
      className="flex flex-col h-full overflow-hidden shrink-0"
      style={{
        width: 320,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        color: 'var(--ink)',
        letterSpacing: '-0.018em',
      }}
      aria-label="카드 편집 좌측 패널"
    >

      {/* ── Header ── */}
      <div
        className="flex items-baseline justify-between shrink-0"
        style={{ padding: '20px 22px 14px' }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', letterSpacing: '-0.025em' }}>
          Cards{' '}
          <span style={{ fontSize: 13, color: 'var(--ink-3)', fontWeight: 500, marginLeft: 4, letterSpacing: 0 }}>
            {cards.length}
          </span>
        </h2>
        <button
          type="button"
          aria-label="카드 추가"
          className="inline-flex items-center justify-center"
          style={{
            width: 28, height: 28, borderRadius: 7,
            borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--border)',
            background: 'var(--surface)', color: 'var(--ink-2)', cursor: 'pointer',
            transition: 'background-color 120ms ease, border-color 120ms ease, color 120ms ease',
          }}
          onMouseEnter={e => {
            const b = e.currentTarget
            b.style.background = 'oklch(97% 0.018 152)'
            b.style.borderColor = 'oklch(82% 0.012 152)'
            b.style.color = 'var(--ink)'
          }}
          onMouseLeave={e => {
            const b = e.currentTarget
            b.style.background = 'var(--surface)'
            b.style.borderColor = 'var(--border)'
            b.style.color = 'var(--ink-2)'
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>

      {/* ── Card outline list ── */}
      <nav style={{ padding: '0 22px' }} className="shrink-0" aria-label="카드 목록">
        {cards.map((card, i) => {
          const isSelected = i === activeCardIdx
          const status = getCardStatus(card)
          const title = getCardTitle(card)

          return (
            <div
              key={card.card_num}
              className="lp-outline-item"
              onClick={() => onSelectCard(i)}
            >
              {isSelected && <span className="lp-sel-bar" />}

              <span style={{
                fontSize: 11, fontWeight: 700,
                color: isSelected ? 'var(--brand)' : 'var(--ink-3)',
                fontVariantNumeric: 'tabular-nums',
                minWidth: 18, letterSpacing: '0.02em',
              }}>
                {pad(card.card_num)}
              </span>

              <span
                className="overflow-hidden text-ellipsis whitespace-nowrap"
                style={{
                  flex: 1,
                  fontSize: 13.5,
                  fontWeight: isSelected ? 700 : 500,
                  color: isSelected ? 'var(--ink)' : 'var(--ink-2)',
                  lineHeight: 1.3,
                  letterSpacing: '-0.022em',
                }}
              >
                {title.length > 18 ? title.slice(0, 18) + '…' : title}
              </span>

              <span
                className="rounded-full shrink-0"
                style={{
                  width: 6, height: 6,
                  background: status === 'crit' ? 'var(--crit)' : status === 'warn' ? 'var(--warn)' : 'var(--ok)',
                  opacity: status === 'ok' ? 0.35 : 1,
                }}
                aria-label={status === 'crit' ? '검토 필요' : status === 'warn' ? '검토 권장' : '정상'}
              />
            </div>
          )
        })}
      </nav>

      {/* ── Section rule ── */}
      <div
        className="flex items-center shrink-0"
        style={{ marginTop: 22, padding: '0 22px', gap: 10 }}
      >
        <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
          Content
        </span>
        <span style={{ flex: 1, height: 1, background: 'var(--border-soft)' }} aria-hidden="true" />
        <span style={{ fontSize: 9.5, fontWeight: 700, color: 'var(--ink-3)', letterSpacing: '0.04em' }}>
          AI 추출
        </span>
      </div>

      {/* ── Content fields ── */}
      <div
        className="flex flex-col overflow-y-auto min-h-0"
        style={{ padding: '14px 22px', gap: 18, flex: 1 }}
      >
        {activeCard?.fields && Object.entries(activeCard.fields).map(([key, fv]) => {
          if (!fv) return null
          const label = FIELD_LABELS[key] ?? key
          const status = getFieldStatus(fv)
          const isCrit = fv.risk_level === 'CRITICAL'
          const isLong = key === 'body' || key === 'description'

          return (
            <div key={key} ref={el => { fieldRefs.current[key] = el }}>
              {/* Field label row */}
              <div className="flex justify-between items-baseline" style={{ marginBottom: 2 }}>
                <label
                  htmlFor={`lp-${key}`}
                  style={{ fontSize: 10.5, fontWeight: 800, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em' }}
                >
                  {label}
                </label>
                {status && (
                  <span
                    className="inline-flex items-center"
                    style={{
                      fontSize: 10, fontWeight: 700, letterSpacing: '-0.005em', gap: 4,
                      color: status === 'crit' ? 'var(--crit)' : status === 'warn' ? 'var(--warn)' : 'var(--ok)',
                    }}
                  >
                    <span
                      className="rounded-full"
                      style={{
                        width: 4, height: 4,
                        background: status === 'crit' ? 'var(--crit)' : status === 'warn' ? 'var(--warn)' : 'var(--ok)',
                      }}
                    />
                    {STATUS_LABEL[status]}
                  </span>
                )}
              </div>

              {/* Input */}
              {isLong ? (
                <textarea
                  id={`lp-${key}`}
                  className="lp-under-textarea"
                  rows={3}
                  value={fv.value ?? ''}
                  onChange={e => onFieldChange(key, e.target.value)}
                />
              ) : (
                <input
                  id={`lp-${key}`}
                  type="text"
                  className={`lp-under-input${isCrit ? ' lp-crit' : ''}`}
                  value={fv.value ?? ''}
                  onChange={e => onFieldChange(key, e.target.value)}
                />
              )}

              {/* CRITICAL hint */}
              {isCrit && fv.source && (
                <p style={{ fontSize: 11, color: 'var(--crit)', marginTop: 6, fontWeight: 500, letterSpacing: '-0.005em', lineHeight: 1.5 }}>
                  ↳ {fv.source.section} · p.{fv.source.page}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* ── Footer / progress ── */}
      <div
        className="shrink-0"
        style={{ padding: '14px 22px 18px', borderTop: '1px solid var(--border-soft)' }}
      >
        <div className="flex items-baseline justify-between">
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-2)', letterSpacing: '0.02em' }}>검토 진행</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>
            {activeCardIdx + 1} / {cards.length}
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={activeCardIdx + 1}
          aria-valuemin={0}
          aria-valuemax={cards.length}
          style={{ height: 4, borderRadius: 2, background: 'var(--border-soft)', marginTop: 7, overflow: 'hidden' }}
        >
          <div
            style={{
              height: '100%',
              background: 'var(--brand)',
              width: `${((activeCardIdx + 1) / cards.length) * 100}%`,
              transition: 'width 250ms ease',
            }}
          />
        </div>
        {critCount > 0 && (
          <div
            className="flex items-center"
            style={{ marginTop: 9, fontSize: 11, color: 'var(--crit)', fontWeight: 600, gap: 6, letterSpacing: '-0.005em' }}
          >
            <span className="rounded-full shrink-0" style={{ width: 5, height: 5, background: 'var(--crit)' }} />
            {critCount}개 항목 검토 필요
          </div>
        )}
      </div>

    </aside>
  )
}
