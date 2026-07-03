'use client'

// 덱 생성 진입 (헌법 v3.0). 논문 PDF + 아트 디렉션(미감 방향)을 받아 단일 저작 시작.
// 아트 디렉션 = 동질화 방지의 핵심: 같은 논문도 방향을 바꿔 다르게 뽑는다.

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import AuthGuard from '@/components/auth/AuthGuard'
import { uploadDeck } from '@/lib/api'

const STYLE_CHIPS = [
  '미드나잇 네온 (어두운 배경 + 형광 강조선)',
  '웜 페이퍼 에디토리얼 (종이빛 + 형광펜)',
  '학교 칠판 (분필 손글씨 느낌)',
  '지브리풍 (부드러운 수채 파스텔)',
  '깔끔한 공공기관 (절제된 네이비·그레이)',
]

function formatSize(bytes: number): string {
  return bytes >= 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)}MB` : `${Math.max(1, Math.round(bytes / 1024))}KB`
}

function DeckNewInner() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [cardCount, setCardCount] = useState(7)
  const [style, setStyle] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const acceptFile = useCallback((f: File | null | undefined) => {
    if (!f) return
    if (f.type !== 'application/pdf' && !f.name.toLowerCase().endsWith('.pdf')) {
      setError('PDF 파일만 올릴 수 있습니다.')
      return
    }
    setError(null)
    setFile(f)
  }, [])

  const submit = useCallback(async () => {
    if (!file) { setError('논문 PDF를 선택해 주세요.'); return }
    setSubmitting(true); setError(null)
    try {
      const r = await uploadDeck(file, cardCount, undefined, style.trim() || undefined)
      router.push(`/deck/${r.data.jobId}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '업로드 실패')
      setSubmitting(false)
    }
  }, [file, cardCount, style, router])

  return (
    <div className="min-h-screen bg-canvas-subtle flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-[560px] bg-surface rounded-2xl border border-border p-8" style={{ wordBreak: 'keep-all' }}>
        <h1 className="text-[20px] font-extrabold text-ink mb-1">논문으로 카드뉴스 만들기</h1>
        <p className="text-[13px] text-ink-3 mb-6">PDF 한 편 → 발행 가능한 7장. 원문 수치는 코드가 대조합니다.</p>

        {/* PDF — 드롭존 히어로: 논문이 무대 주인공 */}
        <input
          ref={inputRef} type="file" accept="application/pdf" className="hidden"
          onChange={(e) => { acceptFile(e.target.files?.[0]); e.target.value = '' }}
        />
        {file ? (
          <div className="flex items-center gap-3 rounded-xl border border-forest-green/40 bg-canvas-subtle p-4 mb-5">
            <svg width="34" height="34" viewBox="0 0 34 34" fill="none" aria-hidden="true" className="shrink-0">
              <rect x="5" y="3" width="24" height="28" rx="3" className="stroke-forest-green" strokeWidth="1.8" fill="none"/>
              <path d="M11 12h12M11 17h12M11 22h7" className="stroke-forest-green" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            <div className="min-w-0 flex-1">
              <p className="text-[13.5px] font-semibold text-ink truncate">{file.name}</p>
              <p className="text-[12px] text-ink-3">PDF · {formatSize(file.size)}</p>
            </div>
            <button type="button" onClick={() => inputRef.current?.click()}
              className="text-[12px] px-3 py-1.5 rounded-lg border border-border text-ink-2 hover:bg-canvas-subtle shrink-0">
              교체
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); acceptFile(e.dataTransfer.files?.[0]) }}
            className={`w-full rounded-xl border-2 border-dashed py-10 px-6 mb-5 text-center transition-colors ${
              dragOver ? 'border-forest-green bg-forest-green/5' : 'border-border hover:border-forest-green/50 hover:bg-canvas-subtle'
            }`}
          >
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true" className="mx-auto mb-3 text-ink-3">
              <rect x="7" y="4" width="26" height="32" rx="3" stroke="currentColor" strokeWidth="1.8" fill="none"/>
              <path d="M14 14h12M14 19h12M14 24h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              <path d="M20 36v-8m0 0-3.5 3.5M20 28l3.5 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <p className="text-[14px] font-semibold text-ink mb-1">논문 PDF를 끌어다 놓으세요</p>
            <p className="text-[12.5px] text-ink-3">또는 클릭해서 파일 선택</p>
          </button>
        )}

        {/* 아트 디렉션 */}
        <label className="block text-[13px] font-semibold text-ink-2 mb-1">아트 디렉션 <span className="text-ink-3 font-normal">(선택 — 비우면 AI가 논문에 맞게 자유 선택)</span></label>
        <p className="text-[12px] text-ink-3 mb-2">원하는 미감을 자연어로. 같은 논문도 방향을 바꿔 다르게 나옵니다.</p>
        <div className="flex flex-wrap gap-2 mb-2">
          {STYLE_CHIPS.map((c) => (
            <button key={c} type="button" onClick={() => setStyle(c)}
              className={`text-[12px] px-3 py-1.5 rounded-full border transition-colors ${style === c ? 'bg-forest-green text-canvas border-forest-green' : 'border-border text-ink-2 hover:bg-canvas-subtle'}`}>
              {c.split(' (')[0]}
            </button>
          ))}
        </div>
        <textarea
          value={style} onChange={(e) => setStyle(e.target.value)}
          placeholder="예: 미드나잇 네온, 학교 칠판, 지브리풍, 깔끔한 공공기관…"
          rows={2}
          className="block w-full text-[13px] rounded-lg border border-border p-3 mb-5 resize-none"
        />

        {/* 장수 */}
        <label className="block text-[13px] font-semibold text-ink-2 mb-2">카드 수: {cardCount}장</label>
        <input type="range" min={3} max={7} value={cardCount} onChange={(e) => setCardCount(Number(e.target.value))} className="w-full mb-6" />

        {error && <p className="text-[12px] text-red-600 mb-3">{error}</p>}

        <button
          onClick={submit} disabled={submitting}
          className="w-full py-3 rounded-xl bg-forest-green text-canvas font-bold text-[14px] disabled:opacity-50"
        >
          {submitting ? '저작 시작 중…' : '카드뉴스 생성'}
        </button>
      </div>
    </div>
  )
}

export default function DeckNewPage() {
  return (
    <AuthGuard>
      <DeckNewInner />
    </AuthGuard>
  )
}
