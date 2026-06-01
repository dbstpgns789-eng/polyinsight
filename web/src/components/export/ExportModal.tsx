'use client'

import { createPortal } from 'react-dom'
import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { triggerExport, getExportDownloadUrl } from '@/lib/api'
import useUiStore from '@/store/uiStore'
import { IconClose, IconCheck, IconDownload, IconWarning, IconRefresh, IconSpinner } from '@/components/ui/Icons'
import type { Card } from '@/types/editor'

type Phase = 'PREFLIGHT' | 'RENDERING' | 'DONE' | 'ERROR'

interface CardData { cards: Card[] }
interface QueryResult { cardData: CardData }

const STEP_LABELS  = ['데이터 파싱 및 요약', '이미지 렌더링', '레이아웃 최적화'] as const
const STAGE_LABELS = ['데이터 파싱 중', '이미지 렌더링 중', '레이아웃 최적화 중', '완료 · 다음 단계로 전환'] as const
const BOUNDS       = [0, 22, 70, 100] as const

function getActiveStep(p: number): number {
  for (let i = BOUNDS.length - 2; i >= 0; i--) {
    if (p >= BOUNDS[i]) return i
  }
  return 0
}

type CardStatus = 'crit' | 'open' | 'done'

function getCardStatus(card: Card): CardStatus {
  const fields = Object.values(card.fields ?? {})
  if (fields.some(f => f?.risk_level === 'CRITICAL')) return 'crit'
  if (fields.some(f => f?.risk_level === 'HIGH' || f?.risk_level === 'MEDIUM')) return 'open'
  return 'done'
}

export default function ExportModal() {
  const closeExportModal = useUiStore((s) => s.closeExportModal)
  const activeJobId = useUiStore((s) => s.activeJobId)
  const qc = useQueryClient()

  const cardData = qc.getQueryData<QueryResult>(['cards', activeJobId])
  const cards = cardData?.cardData?.cards ?? []

  const reviewedCount   = cards.filter(c => getCardStatus(c) === 'done').length
  const unreviewedCount = cards.length - reviewedCount
  const critCardCount   = cards.filter(c => getCardStatus(c) === 'crit').length

  const [phase, setPhase]       = useState<Phase>('PREFLIGHT')
  const [exportId, setExportId] = useState<string | null>(null)
  const [error, setError]       = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  const activeStep = getActiveStep(Math.round(progress))

  useEffect(() => {
    if (phase !== 'RENDERING') return
    const CEILING = 96
    const id = setInterval(() => {
      setProgress(prev => {
        if (prev >= CEILING) return prev
        const step = Math.max(0.4, (CEILING - prev) * 0.035)
        return Math.min(CEILING, prev + step + Math.random() * 0.8)
      })
    }, 480)
    return () => clearInterval(id)
  }, [phase])

  const handleExport = async () => {
    if (!activeJobId) return
    setProgress(0)
    setPhase('RENDERING')
    try {
      const res = await triggerExport(activeJobId)
      setExportId(res.data.exportId)
      setProgress(100)
      setTimeout(() => setPhase('DONE'), 600)
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류')
      setProgress(100)
      setTimeout(() => setPhase('ERROR'), 400)
    }
  }

  const isRendering = phase === 'RENDERING'

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-ink/20 backdrop-blur-sm"
        onClick={() => !isRendering && closeExportModal()}
      />

      {/* ── PREFLIGHT ── */}
      {phase === 'PREFLIGHT' && (
        <div
          className="relative w-full max-w-[520px] bg-canvas rounded-[20px] border border-border-subtle overflow-hidden"
          style={{ boxShadow: 'var(--shadow-modal)' }}
          role="dialog" aria-modal="true" aria-labelledby="preflight-title"
        >
          {/* Header */}
          <div style={{ padding: '24px 26px 18px' }}>
            <div className="flex items-start justify-between" style={{ gap: 16 }}>
              <div>
                {/* Eyebrow */}
                <div className="inline-flex items-center" style={{ gap: 7, marginBottom: 9 }}>
                  <span
                    className="inline-flex items-center justify-center"
                    style={{ height: 17, padding: '0 7px', borderRadius: 999, background: 'var(--accent-faint)', color: 'var(--accent-hover)', fontSize: 10, fontWeight: 800, letterSpacing: '0.06em' }}
                  >
                    PHASE 1
                  </span>
                  <span style={{ fontSize: 10.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.13em', color: 'var(--brand)' }}>
                    Preflight · 사전 확인
                  </span>
                </div>
                <h2
                  id="preflight-title"
                  style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--ink)', lineHeight: 1.15 }}
                >
                  내보내기 준비
                </h2>
              </div>
              <button
                onClick={closeExportModal}
                className="inline-flex items-center justify-center shrink-0 transition-colors"
                style={{ width: 34, height: 34, borderRadius: 10, border: 0, background: 'transparent', color: 'var(--ink-3)', cursor: 'pointer', marginTop: -4, marginRight: -6 }}
                onMouseEnter={e => { const b = e.currentTarget; b.style.background = 'oklch(97.5% 0.012 152)'; b.style.color = 'var(--ink)' }}
                onMouseLeave={e => { const b = e.currentTarget; b.style.background = 'transparent'; b.style.color = 'var(--ink-3)' }}
                aria-label="닫기"
              >
                <IconClose size={19} />
              </button>
            </div>
            <p style={{ marginTop: 6, fontSize: 13.5, color: 'var(--ink-2)', letterSpacing: '-0.015em', lineHeight: 1.5 }}>
              내보내기 전 현재 작업 상태를 확인하고 진행 여부를 결정하세요.
            </p>
          </div>

          {/* Body */}
          <div style={{ padding: '4px 26px 22px', display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Stat — 생성 카드 */}
            <div className="rounded-[14px] border" style={{ background: 'oklch(97.5% 0.012 152)', borderColor: 'var(--border-subtle)', padding: '15px 16px 16px' }}>
              <div className="flex items-center" style={{ gap: 6, marginBottom: 9 }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>
                </svg>
                <span style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.11em', color: 'var(--ink-3)' }}>생성 카드</span>
              </div>
              <div className="flex items-baseline" style={{ gap: 6 }}>
                <span style={{ fontSize: 27, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--ink)', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
                  {cards.length}
                </span>
                <span style={{ fontSize: 13, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink-2)' }}>Cards</span>
              </div>
            </div>

            {/* Per-card review strip */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div className="flex items-baseline justify-between">
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-2)', letterSpacing: '0.01em' }}>카드별 검토 현황</span>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--ink-3)', fontVariantNumeric: 'tabular-nums' }}>
                  <span style={{ color: 'var(--brand)' }}>{reviewedCount}</span> / {cards.length} 검토 완료
                </span>
              </div>
              <div className="flex items-center" style={{ gap: 6 }} aria-hidden="true">
                {cards.length > 0
                  ? cards.map((card, i) => {
                      const s = getCardStatus(card)
                      return (
                        <div
                          key={i}
                          className="flex-1 rounded-full"
                          style={{ height: 6, background: s === 'crit' ? 'var(--crit)' : s === 'done' ? 'var(--brand)' : 'var(--border)' }}
                        />
                      )
                    })
                  : <div className="flex-1 rounded-full" style={{ height: 6, background: 'var(--border)' }} />
                }
              </div>
            </div>

            {/* Conditional notice */}
            {unreviewedCount > 0 ? (
              <div
                className="flex items-start rounded-[14px]"
                style={{ gap: 13, padding: '15px 16px', border: '1px solid var(--risk-critical-line)', background: 'var(--risk-critical-faint)' }}
              >
                <span
                  className="inline-flex items-center justify-center rounded-full shrink-0"
                  style={{ width: 30, height: 30, background: 'var(--crit)', color: '#fff', marginTop: 1 }}
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>
                    <path d="M12 9v4M12 17h.01"/>
                  </svg>
                </span>
                <div className="min-w-0">
                  <p style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--ink)', lineHeight: 1.3 }}>
                    검토하지 않은 항목{' '}
                    <span style={{ color: 'var(--crit)', fontWeight: 800 }}>{unreviewedCount}개</span>
                    {' '}가 남아 있습니다.
                  </p>
                  <p style={{ marginTop: 4, fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-2)', letterSpacing: '-0.012em' }}>
                    검토되지 않은 항목은 원본과 다를 수 있습니다.
                    {critCardCount > 0 && (
                      <> 이 중 <span style={{ color: 'var(--crit)', fontWeight: 800 }}>정합성 불일치 {critCardCount}건</span>이 포함되어 있습니다.</>
                    )}
                    {' '}확인 후 진행하시겠습니까?
                  </p>
                </div>
              </div>
            ) : (
              <div
                className="flex items-start rounded-[14px]"
                style={{ gap: 13, padding: '15px 16px', border: '1px solid var(--border-subtle)', background: 'oklch(98% 0.005 152)' }}
              >
                <span
                  className="inline-flex items-center justify-center rounded-full shrink-0"
                  style={{ width: 30, height: 30, background: 'var(--ok)', color: '#fff', marginTop: 1 }}
                >
                  <IconCheck size={16} />
                </span>
                <div className="min-w-0">
                  <p style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--ink)', lineHeight: 1.3 }}>
                    모든 항목 검토 완료
                  </p>
                  <p style={{ marginTop: 4, fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-2)', letterSpacing: '-0.012em' }}>
                    내보내기를 진행할 준비가 되었습니다.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="flex items-center justify-between border-t"
            style={{ background: 'oklch(98% 0.005 152)', borderColor: 'var(--border-subtle)', padding: '16px 26px', gap: 12 }}
          >
            <div className="flex items-center" style={{ gap: 6, fontSize: 11.5, color: 'var(--ink-3)', letterSpacing: '-0.01em' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
              </svg>
              <span>{unreviewedCount > 0 ? `미검토 ${unreviewedCount}개 · 그대로 진행 가능` : '다음 단계: 생성'}</span>
            </div>
            <div className="flex items-center" style={{ gap: 8 }}>
              <button
                onClick={closeExportModal}
                className="inline-flex items-center justify-center transition-colors"
                style={{ height: 40, padding: '0 16px', borderRadius: 10, border: 0, background: 'transparent', color: 'var(--ink-2)', fontFamily: 'inherit', fontSize: 14, fontWeight: 700, letterSpacing: '-0.015em', cursor: 'pointer' }}
                onMouseEnter={e => { const b = e.currentTarget; b.style.background = 'oklch(97.5% 0.012 152)'; b.style.color = 'var(--ink)' }}
                onMouseLeave={e => { const b = e.currentTarget; b.style.background = 'transparent'; b.style.color = 'var(--ink-2)' }}
              >
                취소
              </button>
              <button
                onClick={handleExport}
                className="inline-flex items-center justify-center transition-colors active:translate-y-[0.5px]"
                style={{ height: 40, padding: '0 20px', borderRadius: 10, border: 0, background: 'var(--brand)', color: '#fff', fontFamily: 'inherit', fontSize: 14, fontWeight: 700, letterSpacing: '-0.015em', cursor: 'pointer', gap: 8, boxShadow: '0 1px 2px oklch(38% 0.14 152 / 0.22)' }}
                onMouseEnter={e => { const b = e.currentTarget; b.style.background = 'var(--accent-hover)' }}
                onMouseLeave={e => { const b = e.currentTarget; b.style.background = 'var(--brand)' }}
              >
                <span>내보내기 시작</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M13 6l6 6-6 6"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── RENDERING ── */}
      {phase === 'RENDERING' && (
        <div
          className="relative w-full bg-canvas rounded-[20px] border overflow-hidden"
          style={{ maxWidth: 520, borderColor: 'var(--border)', boxShadow: 'var(--shadow-modal)' }}
          role="dialog" aria-modal="true" aria-labelledby="rendering-title" aria-busy="true"
        >
          {/* Header */}
          <div style={{ padding: '38px 36px 8px', textAlign: 'center' }}>
            <span
              className="inline-flex items-center justify-center rounded-full"
              style={{ width: 52, height: 52, background: 'oklch(96% 0.03 152)', color: 'var(--brand)', display: 'inline-flex', marginBottom: 18 }}
              aria-hidden="true"
            >
              <svg
                className="render-spinner"
                style={{ width: 26, height: 26 }}
                viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
              >
                <path d="M21 12a9 9 0 1 1-2.64-6.36"/>
                <path d="M21 4v5h-5"/>
              </svg>
            </span>
            <h2
              id="rendering-title"
              style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--ink)', lineHeight: 1.2 }}
            >
              카드 뉴스 생성 중
            </h2>
            <p style={{ marginTop: 9, fontSize: 13.5, color: 'var(--ink-2)', letterSpacing: '-0.015em', lineHeight: 1.6 }}>
              학술 논문을 고해상도 이미지로 변환하고 있습니다.<br />잠시만 기다려 주세요.
            </p>
          </div>

          {/* Body */}
          <div style={{ padding: '24px 36px 6px' }}>
            {/* Progress bar */}
            <div
              className="relative w-full rounded-full overflow-hidden"
              style={{ height: 6, background: 'oklch(93% 0.03 152)' }}
              role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}
            >
              <div
                className="export-bar-fill"
                style={{ width: `${Math.round(progress)}%`, background: 'var(--brand)', transition: 'width 420ms cubic-bezier(0.4, 0, 0.2, 1)' }}
              />
            </div>
            <div className="flex items-baseline justify-between" style={{ marginTop: 11 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-2)', letterSpacing: '-0.01em' }}>
                {progress >= 100 ? STAGE_LABELS[3] : STAGE_LABELS[activeStep]}
              </span>
              <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--brand)', fontVariantNumeric: 'tabular-nums', letterSpacing: '0.01em' }}>
                {Math.round(progress)}%
              </span>
            </div>

            {/* Steps */}
            <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 2 }}>
              {STEP_LABELS.map((label, i) => {
                const isDone   = i < activeStep || progress >= 100
                const isActive = i === activeStep && progress < 100
                return (
                  <div
                    key={i}
                    className="flex items-center"
                    style={{ gap: 12, padding: '9px 0', opacity: (!isDone && !isActive) ? 0.45 : 1, transition: 'opacity 300ms ease' }}
                  >
                    <span
                      className="inline-flex items-center justify-center rounded-full shrink-0"
                      style={{
                        width: 22, height: 22,
                        borderWidth: isDone ? 0 : isActive ? 2 : 1.5,
                        borderStyle: 'solid',
                        borderColor: isDone ? 'transparent' : isActive ? 'var(--brand)' : 'var(--border)',
                        background: isDone ? 'var(--ok)' : 'var(--surface)',
                        color: isDone ? '#fff' : 'transparent',
                        transition: 'all 300ms ease',
                      }}
                    >
                      {isDone && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 6 9 17l-5-5"/>
                        </svg>
                      )}
                      {isActive && (
                        <span className="export-step-pip rounded-full" style={{ background: 'var(--brand)' }} />
                      )}
                    </span>
                    <span style={{
                      fontSize: 13.5, letterSpacing: '-0.015em',
                      fontWeight: isDone ? 600 : isActive ? 700 : 500,
                      color: isDone ? 'var(--ink-2)' : isActive ? 'var(--brand)' : 'var(--ink-3)',
                      transition: 'color 300ms ease',
                    }}>
                      {isDone ? `${label} 완료` : isActive ? `${label} 중…` : `${label} 대기`}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Footer */}
          <div style={{ padding: '18px 36px 30px', textAlign: 'center' }}>
            <p
              className="inline-flex items-center justify-center"
              style={{ fontSize: 10.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--ink-3)', marginBottom: 16, gap: 8 }}
            >
              <span className="export-live-dot rounded-full" style={{ background: 'var(--brand)' }} />
              고해상도 렌더링 엔진 작동 중
            </p>
            <button
              disabled
              className="w-full inline-flex items-center justify-center"
              style={{ height: 46, borderRadius: 10, border: 0, background: 'oklch(97.5% 0.012 152)', color: 'var(--ink-3)', fontFamily: 'inherit', fontSize: 13.5, fontWeight: 700, letterSpacing: '-0.01em', cursor: 'not-allowed', gap: 8 }}
              aria-disabled="true"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="5" y="11" width="14" height="10" rx="2"/>
                <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
              </svg>
              <span>중단 불가 · 처리 중</span>
            </button>
          </div>

          {/* Bottom accent */}
          <div className="export-accent" aria-hidden="true" />
        </div>
      )}

      {/* ── DONE ── */}
      {phase === 'DONE' && exportId && (
        <div
          className="relative w-full bg-canvas rounded-[20px] border overflow-hidden"
          style={{ maxWidth: 520, borderColor: 'var(--border)', boxShadow: 'var(--shadow-modal)' }}
          role="dialog" aria-modal="true" aria-labelledby="done-title"
        >
          {/* Header */}
          <div style={{ padding: '34px 32px 22px', textAlign: 'center' }}>
            <span className="export-done-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5"/>
              </svg>
            </span>
            <h2
              id="done-title"
              style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--ink)', lineHeight: 1.2 }}
            >
              내보내기 완료
            </h2>
            <p style={{ marginTop: 7, fontSize: 14, color: 'var(--ink-2)', letterSpacing: '-0.015em' }}>
              총 <b style={{ color: 'var(--ink)', fontWeight: 700 }}>{cards.length}</b>장의 카드 뉴스가 성공적으로 생성되었습니다.
            </p>
          </div>

          {/* ZIP download */}
          <div style={{ padding: '0 32px 24px' }}>
            <a
              href={getExportDownloadUrl(exportId)}
              download="polyinsight_cards.zip"
              className="flex items-center justify-center"
              style={{
                gap: 10, width: '100%', height: 52, borderRadius: 14,
                background: 'var(--brand)', color: '#fff',
                fontFamily: 'inherit', fontSize: 14.5, fontWeight: 700, letterSpacing: '-0.015em',
                textDecoration: 'none', boxShadow: '0 1px 2px oklch(38% 0.14 152 / 0.22)',
                transition: 'background-color 120ms ease, box-shadow 150ms ease',
              }}
              onMouseEnter={e => { const a = e.currentTarget; a.style.background = 'var(--accent-hover)'; a.style.boxShadow = '0 6px 16px oklch(38% 0.14 152 / 0.26)' }}
              onMouseLeave={e => { const a = e.currentTarget; a.style.background = 'var(--brand)'; a.style.boxShadow = '0 1px 2px oklch(38% 0.14 152 / 0.22)' }}
            >
              <svg style={{ width: 17, height: 17, flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>
              </svg>
              <span>전체 다운로드 (ZIP)</span>
              <span style={{ opacity: 0.7, fontWeight: 600, fontSize: 12.5 }}>· {cards.length}개 파일</span>
            </a>
          </div>

          {/* Individual files */}
          <div style={{ background: 'oklch(97.5% 0.012 152)', borderTop: '1px solid var(--border)', padding: '22px 32px 24px' }}>
            <div className="flex items-baseline justify-between" style={{ marginBottom: 14 }}>
              <span style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.13em', color: 'var(--ink-3)' }}>
                개별 파일 다운로드
              </span>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-3)', fontVariantNumeric: 'tabular-nums' }}>
                {cards.length}개 PNG
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 9 }}>
              {cards.map((card) => {
                const name = `card_${String(card.card_num).padStart(2, '0')}.png`
                return (
                  <a
                    key={card.card_num}
                    href={`/api/cards/${activeJobId}/image/${card.card_num}`}
                    download={name}
                    className="flex items-center justify-between"
                    style={{
                      gap: 10, padding: '11px 12px',
                      background: 'var(--surface)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--border)',
                      borderRadius: 10, textDecoration: 'none',
                      transition: 'border-color 130ms ease, box-shadow 130ms ease',
                    }}
                    onMouseEnter={e => { const a = e.currentTarget; a.style.borderColor = 'var(--brand)'; a.style.boxShadow = '0 2px 8px oklch(38% 0.14 152 / 0.1)' }}
                    onMouseLeave={e => { const a = e.currentTarget; a.style.borderColor = 'var(--border)'; a.style.boxShadow = 'none' }}
                  >
                    <span className="flex items-center min-w-0" style={{ gap: 11 }}>
                      <span
                        className="inline-flex items-center justify-center shrink-0"
                        style={{ width: 30, height: 30, borderRadius: 7, background: 'oklch(96% 0.03 152)', color: 'var(--brand)' }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="3" width="18" height="18" rx="3"/>
                          <circle cx="8.5" cy="8.5" r="1.6"/>
                          <path d="m21 16-4.5-4.5L7 21"/>
                        </svg>
                      </span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.01em', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {name}
                      </span>
                    </span>
                    <span className="inline-flex shrink-0" style={{ color: 'var(--ink-3)', transition: 'color 130ms ease' }}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>
                      </svg>
                    </span>
                  </a>
                )
              })}
            </div>
          </div>

          {/* Footer */}
          <div
            className="flex items-center justify-between border-t"
            style={{ padding: '16px 32px', borderColor: 'var(--border)', background: 'var(--surface)', gap: 12 }}
          >
            <span style={{ fontSize: 11.5, color: 'var(--ink-3)', letterSpacing: '-0.01em' }}>
              다운로드 후 모달을 닫아도 됩니다.
            </span>
            <button
              onClick={closeExportModal}
              className="inline-flex items-center justify-center transition-colors"
              style={{ height: 40, padding: '0 20px', borderRadius: 10, border: 0, background: 'oklch(97.5% 0.012 152)', color: 'var(--ink-2)', fontFamily: 'inherit', fontSize: 14, fontWeight: 700, letterSpacing: '-0.015em', cursor: 'pointer' }}
              onMouseEnter={e => { const b = e.currentTarget; b.style.background = 'var(--border-soft)'; b.style.color = 'var(--ink)' }}
              onMouseLeave={e => { const b = e.currentTarget; b.style.background = 'oklch(97.5% 0.012 152)'; b.style.color = 'var(--ink-2)' }}
            >
              닫기
            </button>
          </div>
        </div>
      )}

      {/* ── ERROR ── */}
      {phase === 'ERROR' && (
        <div
          className="relative w-full bg-canvas rounded-[20px] border overflow-hidden"
          style={{ maxWidth: 520, borderColor: 'var(--border)', boxShadow: 'var(--shadow-modal)' }}
          role="alertdialog" aria-modal="true" aria-labelledby="error-title"
        >
          {/* Header */}
          <div style={{ padding: '34px 32px 4px', textAlign: 'center' }}>
            <span className="export-error-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>
                <path d="M12 9v4M12 17h.01"/>
              </svg>
            </span>
            <p style={{ fontSize: 10.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.13em', color: 'var(--crit)', marginBottom: 5 }}>
              Export Failed
            </p>
            <h2
              id="error-title"
              style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--ink)', lineHeight: 1.2 }}
            >
              내보내기 실패
            </h2>
          </div>

          {/* Body */}
          <div style={{ padding: '9px 32px 24px', textAlign: 'center' }}>
            <p style={{ fontSize: 14, lineHeight: 1.65, color: 'var(--ink-2)', letterSpacing: '-0.015em', maxWidth: 380, margin: '0 auto' }}>
              이미지 생성 중 오류가 발생했습니다. 다시 시도해 주세요. 문제가 계속되면 관리자에게 문의해 주시기 바랍니다.
            </p>
            {error && (
              <div
                className="flex items-start text-left"
                style={{ marginTop: 18, gap: 11, padding: '13px 14px', borderRadius: 10, background: 'oklch(97.5% 0.012 152)', border: '1px solid var(--border)' }}
              >
                <span className="inline-flex shrink-0" style={{ color: 'var(--ink-3)', marginTop: 1 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16h.01"/>
                  </svg>
                </span>
                <div className="min-w-0 flex-1">
                  <p style={{ fontSize: 9.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.14em', color: 'var(--ink-3)', marginBottom: 4 }}>
                    Error Detail
                  </p>
                  <code style={{ fontFamily: "'SFMono-Regular', ui-monospace, 'JetBrains Mono', monospace", fontSize: 12, lineHeight: 1.5, color: 'var(--ink)', wordBreak: 'break-all', display: 'block' }}>
                    {error}
                  </code>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="flex items-center justify-center border-t"
            style={{ padding: '16px 32px 22px', borderColor: 'var(--border-soft)', background: 'oklch(98% 0.005 152)', gap: 8 }}
          >
            <button
              onClick={closeExportModal}
              className="inline-flex items-center justify-center transition-colors"
              style={{ height: 44, padding: '0 24px', borderRadius: 10, border: 0, background: 'oklch(97.5% 0.012 152)', color: 'var(--ink-2)', fontFamily: 'inherit', fontSize: 14, fontWeight: 700, letterSpacing: '-0.015em', cursor: 'pointer' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--ink)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-2)')}
            >
              취소
            </button>
            <button
              onClick={() => { setPhase('PREFLIGHT'); setProgress(0) }}
              className="export-retry-btn inline-flex items-center justify-center transition-colors active:translate-y-[0.5px]"
              style={{ height: 44, padding: '0 28px', borderRadius: 10, border: 0, background: 'var(--brand)', color: '#fff', fontFamily: 'inherit', fontSize: 14, fontWeight: 700, letterSpacing: '-0.015em', cursor: 'pointer', gap: 8, boxShadow: '0 1px 2px oklch(38% 0.14 152 / 0.22)' }}
              onMouseEnter={e => { const b = e.currentTarget; b.style.background = 'var(--accent-hover)'; b.style.boxShadow = '0 3px 10px oklch(38% 0.14 152 / 0.24)' }}
              onMouseLeave={e => { const b = e.currentTarget; b.style.background = 'var(--brand)'; b.style.boxShadow = '0 1px 2px oklch(38% 0.14 152 / 0.22)' }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12a9 9 0 1 0 2.64-6.36"/>
                <path d="M3 4v5h5"/>
              </svg>
              <span>다시 시도</span>
            </button>
          </div>
        </div>
      )}
    </div>,
    document.body
  )
}
