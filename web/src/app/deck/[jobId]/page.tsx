'use client'

// 단일 저작 덱 뷰 (헌법 v3.0). 발행 가능한 PNG 카드 피드 + 충실성 검증 패널(해자).
// 편집은 Phase 3(WYSIWYG). 지금은 view + export.

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import AuthGuard from '@/components/auth/AuthGuard'
import { getStatus, getDeck, exportDeck, getDeckCardUrl, getExportDownloadUrl } from '@/lib/api'

interface VerifyClaim { value: string; context: string; verified: boolean }
interface VerifyData { verified: number; unverified: number; claims: VerifyClaim[] }
interface DeckPayload {
  jobId: string; filename?: string; status: string; warnings?: string[]
  html?: string | null; verify?: VerifyData | null; cardCount: number
}

function abortReason(warnings?: string[]): string | null {
  const w = (warnings ?? []).find((x) => x.startsWith('ABORT-') || x.startsWith('ERR-'))
  return w ? w.replace(/^(ABORT|ERR)-[A-Z0-9]*:\s*/, '') : null
}

function DeckPageInner() {
  const { jobId } = useParams() as { jobId: string }
  const [status, setStatus] = useState<string>('PENDING')
  const [stage, setStage] = useState<string>('')
  const [deck, setDeck] = useState<DeckPayload | null>(null)
  const [exporting, setExporting] = useState(false)

  // 상태 폴링 → DONE이면 덱 로드
  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const r = await getStatus(jobId)
        if (cancelled) return
        setStatus(r.data.status)
        setStage(r.data.stage ?? '')
        if (r.data.status === 'DONE' || r.data.status === 'ERROR') {
          const d = await getDeck(jobId)
          if (!cancelled) setDeck(d.data as DeckPayload)
          return
        }
      } catch { /* 폴링 재시도 */ }
      if (!cancelled) timer = setTimeout(poll, 1500)
    }
    poll()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [jobId])

  const handleExport = useCallback(async () => {
    setExporting(true)
    try {
      const r = await exportDeck(jobId)
      window.location.href = getExportDownloadUrl(r.data.exportId)
    } finally { setExporting(false) }
  }, [jobId])

  // ── 진행 중 ──
  if (status !== 'DONE' && status !== 'ERROR') {
    return (
      <div className="flex items-center justify-center h-screen bg-canvas-subtle">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-forest-green border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-[13px] text-ink-3">덱 생성 중… {stage && `(${stage})`}</p>
        </div>
      </div>
    )
  }

  // ── 실패 ──
  if (status === 'ERROR' || !deck?.html) {
    const reason = abortReason(deck?.warnings)
    return (
      <div className="flex items-center justify-center h-screen bg-canvas-subtle">
        <div className="text-center max-w-md px-6">
          <p className="text-4xl mb-3">⚠️</p>
          <p className="text-[14px] text-ink-2 font-medium">{reason || '덱을 생성하지 못했습니다.'}</p>
          <p className="text-[12px] text-ink-3 mt-2">다른 논문 PDF로 다시 시도해 주세요.</p>
        </div>
      </div>
    )
  }

  const v = deck.verify
  const flagged = v?.claims.filter((c) => !c.verified) ?? []
  const cardNums = Array.from({ length: deck.cardCount || 7 }, (_, i) => i + 1)

  return (
    <div className="flex h-screen overflow-hidden bg-canvas-subtle" style={{ wordBreak: 'keep-all' }}>
      {/* 카드 피드 */}
      <main className="flex-1 overflow-y-auto py-10 flex flex-col items-center gap-8">
        <div className="w-full max-w-[460px] flex items-center justify-between px-1">
          <span className="text-[14px] font-semibold text-ink truncate">{deck.filename}</span>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="text-[13px] font-semibold px-4 py-2 rounded-lg bg-forest-green text-canvas disabled:opacity-50"
          >
            {exporting ? '내보내는 중…' : 'ZIP 내보내기'}
          </button>
        </div>
        {cardNums.map((n) => (
          <img
            key={n}
            src={getDeckCardUrl(deck.jobId, n)}
            alt={`card ${n}`}
            className="w-full max-w-[460px] rounded-[10px] shadow-md"
            style={{ aspectRatio: '1080 / 1350', objectFit: 'cover', background: '#11152B' }}
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
          />
        ))}
      </main>

      {/* 검증 패널 (해자) */}
      <aside className="w-[360px] shrink-0 border-l border-border bg-surface overflow-y-auto p-6">
        <h2 className="text-[15px] font-bold text-ink mb-1">충실성 검증</h2>
        <p className="text-[12px] text-ink-3 mb-5">막지 않고, 출처를 분류해 보여줍니다. 최종 판단은 사용자.</p>

        <div className="flex gap-3 mb-6">
          <div className="flex-1 rounded-xl border border-border p-3 text-center">
            <div className="text-[22px] font-extrabold text-forest-green">{v?.verified ?? 0}</div>
            <div className="text-[11px] text-ink-3 mt-1">논문 근거 확인</div>
          </div>
          <div className="flex-1 rounded-xl border border-border p-3 text-center">
            <div className="text-[22px] font-extrabold text-amber-600">{v?.unverified ?? 0}</div>
            <div className="text-[11px] text-ink-3 mt-1">사용자 판단 필요</div>
          </div>
        </div>

        {flagged.length > 0 ? (
          <div>
            <p className="text-[12px] font-semibold text-ink-2 mb-2">
              ⚠️ 원문에 없는 수치 — AI가 더한 맥락/예시인지 확인하세요:
            </p>
            <ul className="flex flex-col gap-2">
              {flagged.map((c, i) => (
                <li key={i} className="rounded-lg border border-border bg-canvas-subtle p-3">
                  <span className="text-[14px] font-bold text-ink">{c.value}</span>
                  <p className="text-[11px] text-ink-3 mt-1 leading-snug">…{c.context}…</p>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-[13px] text-ink-3">모든 수치가 원문에서 추적됐습니다.</p>
        )}
      </aside>
    </div>
  )
}

export default function DeckPage() {
  return (
    <AuthGuard>
      <DeckPageInner />
    </AuthGuard>
  )
}
