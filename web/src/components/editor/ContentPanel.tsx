'use client'

import { useEffect, useRef, useState } from 'react'
import type { RiskLevel, FieldValue, Card } from '@/types/editor'

const CONF_KO: Record<string, string> = { high: '양호', medium: '보통', low: '주의' }

const TEMPLATE_LABELS: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제제기', circle3: '3포인트',
  compare2: '비교', grid4: '4분면', definition: '정의', flow: '흐름도',
  data: '데이터', showcase: '성과', closing: '마무리', brand: '브랜딩',
}

const FIELD_LABELS: Record<string, string> = {
  title: '제목',
  subtitle: '부제목',
  body: '본문',
  description: '설명',
  section_title: '섹션 제목',
  stat_main: '주요 수치',
  stat_desc: '수치 설명',
  stat_sub: '보조 수치',
  citation: '출처',
  institution: '기관',
  author: '저자',
  step1: '단계 1',
  step2: '단계 2',
  step3: '단계 3',
  step4: '단계 4',
}

function pad(n: number) { return String(n).padStart(2, '0') }

function getCardTitle(card: Card): string {
  const f = card.fields ?? {}
  return (
    f.title?.value ||
    f.section_title?.value ||
    TEMPLATE_LABELS[card.template_type] ||
    card.template_type
  )
}

function RiskBadge({ risk }: { risk?: RiskLevel }) {
  if (!risk) return null
  const cls =
    risk === 'CRITICAL' ? 'bg-risk-critical-bg text-risk-critical border-risk-critical/20' :
    risk === 'HIGH'     ? 'bg-risk-high-bg text-risk-high border-risk-high/20' :
    risk === 'MEDIUM'   ? 'bg-risk-medium-bg text-risk-medium border-risk-medium/20' : ''
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${cls}`}>
      {risk}
    </span>
  )
}

function FieldEditor({
  fieldKey, fieldValue, onChange, onConfirmRisk, isHighlighted,
  fieldRef,
}: {
  fieldKey: string
  fieldValue: FieldValue
  onChange: (key: string, value: string) => void
  onConfirmRisk: (key: string) => void
  isHighlighted: boolean
  fieldRef: (el: HTMLDivElement | null) => void
}) {
  const risk = fieldValue?.risk_level
  const conf = fieldValue?.confidence ?? ''
  const fieldId = `field-${fieldKey}`

  const fieldClass =
    isHighlighted    ? 'ep-field ep-field--highlighted' :
    risk === 'CRITICAL' ? 'ep-field ep-field--critical' :
    risk === 'HIGH'     ? 'ep-field ep-field--high' :
    risk === 'MEDIUM'   ? 'ep-field ep-field--medium' :
    'ep-field'

  return (
    <div ref={fieldRef} className={fieldClass}>
      <div className="ep-field-header">
        <label className="ep-field-label" htmlFor={fieldId}>
          {FIELD_LABELS[fieldKey] ?? fieldKey}
        </label>
        <div className="flex items-center gap-1.5">
          {conf && (
            <span className={`ep-conf ep-conf--${conf}`}>
              {CONF_KO[conf] ?? conf}
            </span>
          )}
          {risk && <RiskBadge risk={risk} />}
        </div>
      </div>

      {risk === 'CRITICAL' && (
        <div className="ep-risk-banner ep-risk-banner--critical">
          <span className="font-bold shrink-0">⚠</span>
          <div>
            <span className="font-bold">원문 대조 필요</span>
            {fieldValue?.source && (
              <span className="ep-risk-source">
                출처: {fieldValue.source.section} · p.{fieldValue.source.page}
              </span>
            )}
          </div>
        </div>
      )}
      {risk === 'HIGH' && (
        <div className="ep-risk-banner ep-risk-banner--high">
          주의가 필요한 항목입니다.
        </div>
      )}

      <textarea
        id={fieldId}
        rows={fieldKey === 'body' || fieldKey === 'description' ? 4 : 2}
        value={fieldValue?.value ?? ''}
        onChange={e => onChange(fieldKey, e.target.value)}
        className="ep-textarea"
      />

      {(risk === 'CRITICAL' || risk === 'HIGH') && (
        <button className="ep-confirm-btn" onClick={() => onConfirmRisk(fieldKey)}>
          확인 완료
        </button>
      )}
    </div>
  )
}

interface Props {
  cards: Card[]
  activeCardIdx: number
  onSelectCard: (idx: number) => void
  onFieldChange: (fieldKey: string, value: string) => void
  onConfirmRisk: (fieldKey: string) => void
  focusedField?: string | null
}

export default function ContentPanel({
  cards, activeCardIdx, onSelectCard, onFieldChange, onConfirmRisk, focusedField,
}: Props) {
  const [highlightedField, setHighlightedField] = useState<string | null>(null)
  const fieldRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!focusedField) return
    setHighlightedField(focusedField)
    const el = fieldRefs.current[focusedField]
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const t = setTimeout(() => setHighlightedField(null), 1800)
    return () => clearTimeout(t)
  }, [focusedField])

  if (!cards?.length) return (
    <div className="flex items-center justify-center h-full text-[12px] text-ink-muted" style={{ width: 280 }}>
      카드 데이터 없음
    </div>
  )

  const activeCard = cards[activeCardIdx]

  return (
    <div className="flex flex-col h-full bg-surface border-r border-surface-border" style={{ width: 280 }}>

      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-surface-border shrink-0">
        <span className="text-[10px] font-bold text-ink-muted uppercase tracking-widest">
          카드 ({cards.length})
        </span>
      </div>

      {/* 카드 목록 */}
      <div className="border-b border-surface-border shrink-0">
        <div className="p-2 space-y-0.5">
          {cards.map((card, idx) => {
            const isActive = idx === activeCardIdx
            const title = getCardTitle(card)
            return (
              <button
                key={card.card_num}
                onClick={() => onSelectCard(idx)}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/40 ${
                  isActive
                    ? 'bg-brand-50 ring-1 ring-brand-600/25'
                    : 'hover:bg-surface-subtle'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`text-[10px] font-bold tabular-nums shrink-0 ${
                    isActive ? 'text-brand-600' : 'text-ink-disabled'
                  }`}>
                    {pad(card.card_num)}
                  </span>
                  <span className={`text-[13px] font-semibold truncate ${
                    isActive ? 'text-ink' : 'text-ink-secondary'
                  }`}>
                    {title || `카드 ${pad(card.card_num)}`}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* 템플릿 배지 */}
      <div className="px-4 py-2 border-b border-surface-border bg-surface-subtle shrink-0 flex items-center gap-2">
        <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-widest">템플릿</span>
        <span className="ep-template-badge">
          {TEMPLATE_LABELS[activeCard?.template_type] ?? activeCard?.template_type}
        </span>
      </div>

      {/* 필드 목록 */}
      <div ref={scrollAreaRef} className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {activeCard?.fields &&
          Object.entries(activeCard.fields).map(([key, fv]) => (
            <FieldEditor
              key={key}
              fieldKey={key}
              fieldValue={fv}
              onChange={onFieldChange}
              onConfirmRisk={onConfirmRisk}
              isHighlighted={highlightedField === key}
              fieldRef={(el) => { fieldRefs.current[key] = el }}
            />
          ))}
      </div>
    </div>
  )
}
