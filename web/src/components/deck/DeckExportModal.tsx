'use client'

// v3 덱 Export 모달 (스펙 §4.6) — Portal, 소프트 경고(하드블록 금지, web/CLAUDE.md §7).
// legacy components/export/ExportModal(uiStore·Card.fields.risk_level 결합) 대체.
// 무료체험 export-gate(402 ERR-PLAN-EXPORT) → 순수잠금 페이월. 워터마크·타이머·닫기숨김 없음.
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { exportDeck, getExportDownloadUrl } from '@/lib/api'
import { planGateKind } from '@/lib/plan'

interface Props {
  jobId: string
  filename: string
  cardCount: number
  unverified: number
  onClose: () => void
}

export default function DeckExportModal({ jobId, filename, cardCount, unverified, onClose }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [paywalled, setPaywalled] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleExport = async () => {
    setBusy(true); setError(null)
    try {
      const r = await exportDeck(jobId)
      window.location.href = getExportDownloadUrl(r.data.exportId)
      onClose()
    } catch (e) {
      setBusy(false)
      if (planGateKind(e) === 'export') {
        setPaywalled(true)
        return
      }
      setError('내보내기에 실패했어요. 잠시 후 다시 시도해 주세요.')
    }
  }

  return createPortal(
    <div
      className={`fixed inset-0 z-50 grid place-items-center p-4 ${paywalled ? 'paywall-overlay' : 'bg-black/40'}`}
      onClick={onClose}
    >
      <div
        className={`w-full ${paywalled ? 'max-w-[440px]' : 'max-w-[400px]'} bg-surface rounded-2xl shadow-modal p-6`}
        onClick={(e) => e.stopPropagation()}
      >
        {paywalled ? (
          <div className="paywall">
            <p className="paywall__eyebrow">✓ 원문 검증 완료</p>
            <h2 className="paywall__title">이 카드뉴스, 내보낼 준비가 끝났어요</h2>

            <div className="paywall__split">
              <div className="paywall__col">
                <p className="paywall__colhead">무료로 받은 것</p>
                <ul>
                  <li>✓ 카드뉴스 저작</li>
                  <li>✓ 원문 수치 검증</li>
                  <li>✓ 화면에서 보기 · 편집</li>
                </ul>
              </div>
              <div className="paywall__col paywall__col--accent">
                <p className="paywall__colhead">업그레이드하면</p>
                <ul>
                  <li>1080×1350 PNG 파일</li>
                  <li>덱 전체 ZIP 내보내기</li>
                  <li>카드뉴스 계속 만들기</li>
                </ul>
              </div>
            </div>

            <div className="paywall__actions">
              <a className="btn btn-primary" href="/upgrade?from=export">업그레이드하고 내보내기</a>
              <button className="btn btn-ghost" onClick={onClose}>계속 둘러보기</button>
            </div>
          </div>
        ) : (
          <>
            <h2 className="text-[16px] font-bold text-ink">내보내기</h2>
            <p className="text-[12px] text-ink-3 mt-1 truncate">{filename}</p>

            <div className="mt-4 rounded-xl border border-border p-3 flex items-center justify-between">
              <span className="text-[12.5px] text-ink-2">카드 {cardCount}장 · PNG ZIP</span>
              <span className="text-[11px] text-ink-3">1080×1350</span>
            </div>

            {unverified >= 1 && (
              <div className="mt-3 rounded-xl border border-risk-medium-border bg-risk-medium-faint p-3">
                <p className="text-[11.5px] text-risk-medium font-semibold">⚠ 확인이 필요한 수치가 {unverified}개 있어요.</p>
                <p className="text-[11px] text-ink-3 mt-1 leading-snug">그래도 내보낼 수 있어요 — 최종 판단은 직접 하세요.</p>
              </div>
            )}

            {error && <p className="mt-3 text-[11.5px] text-risk-medium">{error}</p>}

            <div className="mt-5 flex gap-2">
              <button onClick={onClose} disabled={busy}
                className="flex-1 h-10 rounded-lg border border-border text-ink-2 text-[13px] font-semibold disabled:opacity-40">취소</button>
              <button onClick={handleExport} disabled={busy}
                className="flex-1 h-10 rounded-lg bg-forest-green text-canvas text-[13px] font-semibold disabled:opacity-40">
                {busy ? '내보내는 중…' : 'ZIP 내보내기'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body,
  )
}
