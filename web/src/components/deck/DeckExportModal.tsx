'use client'

// v3 덱 Export 모달 (스펙 §4.6) — Portal, 소프트 경고(하드블록 금지, web/CLAUDE.md §7).
// 무료체험 export-gate(402 ERR-PLAN-EXPORT) → 순수잠금 페이월. 워터마크·타이머·닫기숨김 없음.
//
// 2026-07-22 리디자인(P0-3, Mirra 벤치마크): 진입 = 정직한 2선택 카드(동등 위계, 색 오버셀 금지,
//   서브텍스트로 "뭘 받는지" 명시). 인스타 = "인스타 게시 준비"(자동 아님 명시) + AI 캡션 전면.
//   ★export/다운로드는 무료(크레딧 차감 X) — Mirra도 다운 무료. 게이트는 plan(무료체험만 페이월).
//   게이팅은 반응형 유지(클릭→402→페이월, WTP 최고조에서 잡음). 캡션 생성은 무료(아하).
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { exportDeck, getDeckCaption, getExportDownloadUrl } from '@/lib/api'
import { buildInstagramCaption } from '@/lib/instagramCaption'
import { planGateKind } from '@/lib/plan'

interface Props {
  jobId: string
  filename: string
  cardCount: number
  unverified: number
  onClose: () => void
}

const IG_LIMIT = 2200  // 인스타 캡션 글자 상한 (초과분은 인스타가 자름)

export default function DeckExportModal({ jobId, filename, cardCount, unverified, onClose }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [paywalled, setPaywalled] = useState(false)

  // Phase 0 인스타 게시 준비
  const [mode, setMode] = useState<'export' | 'instagram'>('export')
  const [caption, setCaption] = useState('')          // 편집 가능한 최종 텍스트(캡션+해시태그)
  const [capLoading, setCapLoading] = useState(false)
  const [capErr, setCapErr] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

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

  const enterInstagram = async () => {
    setMode('instagram'); setCapErr(null); setCopied(false)
    if (caption) return                 // 이미 받아둠(재진입 시 재요청 안 함)
    setCapLoading(true)
    try {
      const r = await getDeckCaption(jobId)
      setCaption(buildInstagramCaption(r.data.caption, r.data.hashtags))
    } catch {
      // 백엔드 캡션 엔드포인트가 아직/실패해도 이미지 다운·인스타 열기는 되게 둔다.
      setCapErr('캡션을 아직 만들 수 없어요. 이미지만 받아 직접 작성해 올릴 수 있어요.')
    } finally {
      setCapLoading(false)
    }
  }

  const copyCaption = async () => {
    try {
      await navigator.clipboard.writeText(caption)
      setCopied(true); setTimeout(() => setCopied(false), 2000)
    } catch {
      setCapErr('복사에 실패했어요. 텍스트를 직접 선택해 복사해 주세요.')
    }
  }

  const openInstagram = () => window.open('https://www.instagram.com/', '_blank', 'noopener')

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
        ) : mode === 'instagram' ? (
          <>
            <div className="flex items-center gap-2">
              <button onClick={() => setMode('export')} aria-label="뒤로"
                className="w-7 h-7 -ml-1 grid place-items-center rounded-lg text-ink-3 hover:bg-bg-subtle text-[16px]">←</button>
              <h2 className="text-[16px] font-bold text-ink">인스타 게시 준비</h2>
            </div>
            <p className="text-[11.5px] text-ink-3 mt-1.5">
              <b className="text-forest-green font-bold">①</b> 캡션 복사 &nbsp;
              <b className="text-forest-green font-bold">②</b> 이미지 받기 &nbsp;
              <b className="text-forest-green font-bold">③</b> 인스타에 붙여넣기
            </p>

            {capLoading ? (
              <div className="mt-4 h-28 rounded-xl border border-border grid place-items-center text-[12.5px] text-ink-3">
                캡션 만드는 중…
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-border overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 bg-forest-green-wash border-b border-border">
                  <span className="text-[11px] font-bold text-forest-green-deep">✦ AI가 쓴 캡션</span>
                  <button onClick={copyCaption} disabled={!caption}
                    className="text-[11.5px] font-bold text-forest-green bg-surface border border-border rounded-lg px-2.5 py-1 disabled:opacity-40">
                    {copied ? '복사됨 ✓' : '복사'}
                  </button>
                </div>
                <textarea
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  placeholder="캡션을 직접 작성하거나 다듬으세요."
                  rows={5}
                  className="w-full px-3 py-3 text-[12.5px] leading-relaxed text-ink resize-none focus:outline-none min-h-[112px]"
                />
                <div className="px-3 py-1.5 border-t border-border text-right">
                  <span className={`text-[10.5px] ${caption.length > IG_LIMIT ? 'text-risk-medium font-semibold' : 'text-ink-3'}`}>
                    {caption.length} / {IG_LIMIT}{caption.length > IG_LIMIT ? ' · 초과분은 인스타가 잘라요' : ''}
                  </span>
                </div>
              </div>
            )}

            {capErr && <p className="mt-3 text-[11.5px] text-risk-medium leading-snug">{capErr}</p>}
            {error && <p className="mt-3 text-[11.5px] text-risk-medium">{error}</p>}

            <div className="mt-4 grid gap-2">
              <button onClick={handleExport} disabled={busy}
                className="h-[42px] rounded-[10px] bg-forest-green text-canvas text-[13.5px] font-bold disabled:opacity-40">
                {busy ? '이미지 준비 중…' : '이미지 받기'}
              </button>
              <button onClick={openInstagram}
                className="h-[42px] rounded-[10px] border border-border text-ink-2 text-[13.5px] font-semibold hover:bg-bg-subtle transition-colors">
                인스타 열기 →
              </button>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-[16px] font-bold text-ink">내보내기</h2>
            <p className="text-[12px] text-ink-3 mt-0.5 truncate">{filename}</p>

            <div className="mt-4 rounded-xl border border-border p-3 flex items-center justify-between">
              <span className="text-[12.5px] text-ink-2 font-medium">카드 {cardCount}장 · PNG</span>
              <span className="text-[11px] text-ink-3">1080×1350</span>
            </div>

            {unverified >= 1 && (
              <div className="mt-3 rounded-xl border border-risk-medium-border bg-risk-medium-faint p-3">
                <p className="text-[11.5px] text-risk-medium font-semibold">⚠ 확인이 필요한 수치가 {unverified}개 있어요</p>
                <p className="text-[11px] text-ink-3 mt-1 leading-snug">그래도 내보낼 수 있어요 — 최종 판단은 직접 하세요.</p>
              </div>
            )}

            {error && <p className="mt-3 text-[11.5px] text-risk-medium">{error}</p>}

            {/* 정직한 2선택 (동등 위계) — 색 오버셀 금지, 서브텍스트로 '뭘 받는지' 명시 */}
            <div className="mt-4 flex flex-col gap-2.5">
              <button onClick={enterInstagram}
                className="flex items-center gap-3 w-full text-left border border-border rounded-xl px-4 py-3 bg-surface hover:bg-bg-subtle transition-colors">
                <span className="w-[38px] h-[38px] shrink-0 rounded-[10px] grid place-items-center text-[19px] bg-bg-subtle">📸</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[14px] font-bold text-ink">인스타에 올리기</span>
                  <span className="block text-[11.5px] text-ink-3 mt-[3px] leading-snug">AI가 캡션까지 써드려요 · 이미지 받아 직접 게시</span>
                </span>
                <span className="text-ink-3 text-[15px] shrink-0" aria-hidden="true">→</span>
              </button>

              <button onClick={handleExport} disabled={busy}
                className="flex items-center gap-3 w-full text-left border border-border rounded-xl px-4 py-3 bg-surface hover:bg-bg-subtle transition-colors disabled:opacity-40">
                <span className="w-[38px] h-[38px] shrink-0 rounded-[10px] grid place-items-center text-[19px] bg-bg-subtle">📦</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[14px] font-bold text-ink">{busy ? '내보내는 중…' : 'ZIP 파일로 받기'}</span>
                  <span className="block text-[11.5px] text-ink-3 mt-[3px] leading-snug">PNG 카드 {cardCount}장 전체 · 어디든 올릴 수 있어요</span>
                </span>
                <span className="text-ink-3 text-[15px] shrink-0" aria-hidden="true">→</span>
              </button>
            </div>

            <button onClick={onClose} disabled={busy}
              className="mt-3.5 w-full text-center text-ink-3 text-[12.5px] font-medium disabled:opacity-40 py-1.5">취소</button>
          </>
        )}
      </div>
    </div>,
    document.body,
  )
}
