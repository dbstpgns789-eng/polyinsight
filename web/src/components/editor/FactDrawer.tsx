// FactDrawer — 화면 하단 팩트 검증 드로어.
//
// 접힘 상태: 48px 고정. CRITICAL/HIGH 건수 요약 + 확장 트리거.
// 펼침 상태: ~320px. 카드별 그룹핑된 risk 필드 목록. 클릭 시 해당 필드 포커스.
//
// EditorPage가 drawerOpen 상태를 관리. FactDrawer는 controlled component.

'use client'

import { useMemo } from 'react'
import type { Card, RiskLevel } from '@/types/editor'

const TEMPLATE_LABEL: Record<string, string> = {
  cover: '표지', hook: '훅', problem: '문제', circle3: '3포인트',
  compare2: '비교', grid4: '4분면', definition: '정의', flow: '흐름',
  data: '데이터', showcase: '성과', closing: '마무리', brand: '브랜드',
  cover_v2: '표지', statement: '진술', feature: '혁신', process_v2: '과정',
  bigstat_compare: '성능', reasons: '근거', grid_v2: '응용', closing_v2: '마무리',
}

interface RiskItem {
  cardIdx: number
  cardNum: number
  templateLabel: string
  fieldKey: string
  value: string
  riskLevel: RiskLevel
  source?: { section: string; page: number }
}

interface Props {
  cards: Card[]
  open: boolean
  onToggle: () => void
  onItemClick: (cardIdx: number, fieldKey: string) => void
  onConfirm?: (cardIdx: number, fieldKey: string) => void
}

function collectRiskItems(cards: Card[]): RiskItem[] {
  const items: RiskItem[] = []
  cards.forEach((card, cardIdx) => {
    if (!card.fields) return
    Object.entries(card.fields).forEach(([fieldKey, fv]) => {
      if (!fv.risk_level) return
      items.push({
        cardIdx,
        cardNum: card.card_num,
        templateLabel: TEMPLATE_LABEL[card.template_type] ?? card.template_type,
        fieldKey,
        value: fv.value ?? '',
        riskLevel: fv.risk_level,
        source: fv.source,
      })
    })
  })
  return items
}

export default function FactDrawer({ cards, open, onToggle, onItemClick, onConfirm }: Props) {
  const items = useMemo(() => collectRiskItems(cards), [cards])
  const criticalCount = items.filter((i) => i.riskLevel === 'CRITICAL').length
  const highCount     = items.filter((i) => i.riskLevel === 'HIGH').length
  const mediumCount   = items.filter((i) => i.riskLevel === 'MEDIUM').length
  const allClear = criticalCount === 0 && highCount === 0 && mediumCount === 0

  return (
    <div
      style={{
        flexShrink: 0,
        zIndex: 50,
        background: 'var(--surface)',
        borderTop: criticalCount > 0 ? '2px solid #DC2626' : '1px solid var(--border)',
        boxShadow: open ? '0 -8px 24px rgba(0,0,0,0.08)' : 'none',
        transition: 'transform 220ms ease',
      }}
    >
      {/* 요약 바 (always visible) */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        style={{
          width: '100%',
          height: 48,
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          padding: '0 22px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        {allClear ? (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            fontSize: 13, fontWeight: 600, color: 'var(--ink-2)',
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%', background: '#16A34A',
            }} />
            모든 필드 검증 완료
          </span>
        ) : (
          <>
            {criticalCount > 0 && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                fontSize: 12, fontWeight: 700,
                color: '#991B1B',
                background: '#FEE2E2',
                padding: '4px 10px', borderRadius: 999,
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#DC2626' }} />
                CRITICAL {criticalCount}건
              </span>
            )}
            {highCount > 0 && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                fontSize: 12, fontWeight: 700,
                color: '#9A3412',
                background: '#FED7AA',
                padding: '4px 10px', borderRadius: 999,
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#EA580C' }} />
                HIGH {highCount}건
              </span>
            )}
            {mediumCount > 0 && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                fontSize: 12, fontWeight: 600,
                color: '#854D0E',
                background: '#FEF3C7',
                padding: '4px 10px', borderRadius: 999,
              }}>
                MEDIUM {mediumCount}건
              </span>
            )}
          </>
        )}
        <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--ink-3)', fontWeight: 600 }}>
          {open ? '닫기' : '검증 패널 열기'}
          <span style={{
            display: 'inline-block',
            transition: 'transform 200ms ease',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          }}>
            ▲
          </span>
        </span>
      </button>

      {/* 펼침 영역 */}
      {open && (
        <div style={{
          maxHeight: '40vh',
          overflowY: 'auto',
          borderTop: '1px solid var(--border)',
          padding: '12px 22px 18px',
        }}>
          {items.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--ink-3)', padding: '12px 0' }}>
              검토가 필요한 필드가 없습니다.
            </p>
          ) : (
            <ul style={{ display: 'flex', flexDirection: 'column', gap: 8, listStyle: 'none' }}>
              {items.map((item, idx) => (
                <RiskRow
                  key={`${item.cardIdx}-${item.fieldKey}-${idx}`}
                  item={item}
                  onItemClick={() => onItemClick(item.cardIdx, item.fieldKey)}
                  onConfirm={onConfirm ? () => onConfirm(item.cardIdx, item.fieldKey) : undefined}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

function RiskRow({
  item, onItemClick, onConfirm,
}: {
  item: RiskItem
  onItemClick: () => void
  onConfirm?: () => void
}) {
  const riskColors = {
    CRITICAL: { fg: '#991B1B', bg: '#FEE2E2', dot: '#DC2626' },
    HIGH:     { fg: '#9A3412', bg: '#FED7AA', dot: '#EA580C' },
    MEDIUM:   { fg: '#854D0E', bg: '#FEF3C7', dot: '#D97706' },
  }[item.riskLevel]

  return (
    <li style={{
      display: 'flex', alignItems: 'flex-start', gap: 12,
      padding: '10px 12px', borderRadius: 8,
      background: 'var(--surface-mid, #FAFBFA)',
      border: '1px solid var(--border-subtle, #E5E7EB)',
    }}>
      <span style={{
        flexShrink: 0,
        display: 'inline-flex', alignItems: 'center', gap: 5,
        fontSize: 10, fontWeight: 700,
        color: riskColors.fg, background: riskColors.bg,
        padding: '3px 7px', borderRadius: 999,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: riskColors.dot }} />
        {item.riskLevel}
      </span>

      <button
        type="button"
        onClick={onItemClick}
        style={{
          flex: 1, textAlign: 'left',
          background: 'transparent', border: 'none', cursor: 'pointer',
          padding: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 3 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-3)', letterSpacing: '0.02em' }}>
            카드 {String(item.cardNum).padStart(2, '0')} · {item.templateLabel}
          </span>
          <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>·</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-2)' }}>{item.fieldKey}</span>
        </div>
        <div style={{
          fontSize: 13, fontWeight: 500, color: 'var(--ink)',
          lineHeight: 1.5,
          overflow: 'hidden', textOverflow: 'ellipsis',
          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
        }}>
          “{item.value || '(빈 값)'}”
        </div>
        {item.source && (
          <div style={{ marginTop: 4, fontSize: 11, color: 'var(--ink-3)' }}>
            ↳ 출처: {item.source.section} · p.{item.source.page}
          </div>
        )}
      </button>

      {onConfirm && (
        <button
          type="button"
          onClick={onConfirm}
          style={{
            flexShrink: 0,
            fontSize: 11, fontWeight: 700,
            color: '#15803D',
            background: '#DCFCE7',
            border: '1px solid #BBF7D0',
            padding: '5px 10px', borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          확인 완료
        </button>
      )}
    </li>
  )
}
