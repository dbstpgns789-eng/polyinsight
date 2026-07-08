'use client'

// 뷰 — 한 장씩 + 썸네일 스트립 (스펙 §4.4, A안). PNG 피드 대체.
import { useEffect, useState } from 'react'
import { getDeckCardUrl } from '@/lib/api'

interface Props {
  jobId: string
  cardCount: number
  ver: number
  rendering?: boolean
  onEditCard: (index: number) => void   // index 0-based
}

export default function DeckViewer({ jobId, cardCount, ver, rendering, onEditCard }: Props) {
  const [idx, setIdx] = useState(0)
  const n = Math.max(cardCount, 1)
  const clamp = (i: number) => Math.max(0, Math.min(i, n - 1))

  const [tick, setTick] = useState(0)
  const [ready, setReady] = useState<Set<number>>(new Set())
  useEffect(() => {
    if (!rendering) return
    const t = setInterval(() => setTick((x) => x + 1), 1500)   // 미완 카드 재시도
    return () => clearInterval(t)
  }, [rendering])
  const markReady = (num: number) => setReady((s) => (s.has(num) ? s : new Set(s).add(num)))

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === 'ArrowLeft') setIdx((i) => clamp(i - 1))
      else if (e.key === 'ArrowRight') setIdx((i) => clamp(i + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [n])

  if (cardCount <= 0) {
    return <div className="grid place-items-center h-full text-[13px] text-ink-3">카드가 아직 없습니다.</div>
  }

  return (
    <div className="flex flex-col items-center gap-4 py-6 h-full overflow-y-auto">
      <div className="relative flex items-center gap-3">
        {n > 1 && (
          <button onClick={() => setIdx((i) => clamp(i - 1))} disabled={idx <= 0} aria-label="이전 카드"
            className="w-9 h-9 rounded-full bg-surface border border-border text-ink-2 shadow-card disabled:opacity-30 shrink-0">‹</button>
        )}
        <div className="relative w-[min(46vh,320px)]" style={{ aspectRatio: '1080 / 1350' }}>
          <CardImg jobId={jobId} num={idx + 1} ver={ver} rendering={rendering} tick={tick} onReady={markReady} />
          {!(rendering && !ready.has(idx + 1)) && (
            <button onClick={() => onEditCard(idx)}
              className="absolute left-1/2 -translate-x-1/2 bottom-3 bg-surface/95 text-forest-green-deep text-[12px] font-bold rounded-lg px-3.5 py-1.5 shadow-modal">
              ✎ 이 카드 편집
            </button>
          )}
        </div>
        {n > 1 && (
          <button onClick={() => setIdx((i) => clamp(i + 1))} disabled={idx >= n - 1} aria-label="다음 카드"
            className="w-9 h-9 rounded-full bg-surface border border-border text-ink-2 shadow-card disabled:opacity-30 shrink-0">›</button>
        )}
      </div>

      {rendering && ready.size < n && (
        <div className="flex items-center gap-2 text-[12px] text-ink-3">
          <span className="w-3.5 h-3.5 rounded-full border-2 border-forest-green border-t-transparent animate-spin" aria-hidden="true" />
          카드 그리는 중 {ready.size} / {n}
        </div>
      )}

      {n > 1 && (
        <div className="flex gap-1.5 flex-wrap justify-center max-w-[80%]">
          {Array.from({ length: n }, (_, i) => (
            <button key={i} onClick={() => setIdx(i)} aria-label={`카드 ${i + 1}`}
              className={`w-8 rounded-md overflow-hidden border ${i === idx ? 'border-forest-green ring-1 ring-forest-green' : 'border-border'}`}
              style={{ aspectRatio: '1080 / 1350' }}>
              <CardImg jobId={jobId} num={i + 1} ver={ver} thumb rendering={rendering} tick={tick} onReady={markReady} />
            </button>
          ))}
        </div>
      )}
      <span className="text-[12px] tabular-nums text-ink-3">{idx + 1} / {n}</span>
    </div>
  )
}

// PNG 로드 — 미완/렌더 중이면 셔머 스켈레톤, 로드되면 fade-in (스펙 §4.4 엣지)
function CardImg({ jobId, num, ver, thumb, rendering, tick, onReady }: {
  jobId: string; num: number; ver: number; thumb?: boolean; rendering?: boolean; tick?: number; onReady?: (n: number) => void
}) {
  const [loaded, setLoaded] = useState(false)
  const bust = rendering ? `${ver}-${tick}` : (ver || undefined)   // 렌더 중엔 tick으로 재시도
  return (
    <div className="w-full h-full rounded-[inherit] overflow-hidden relative">
      {!loaded && <div className="absolute inset-0 pi-shimmer" aria-hidden="true" />}
      <img key={bust} src={getDeckCardUrl(jobId, num, bust)} alt={`카드 ${num}`}
        className={`w-full h-full object-cover rounded-[inherit] transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
        style={thumb ? undefined : { boxShadow: loaded ? 'var(--shadow-modal)' : 'none' }}
        onLoad={() => { setLoaded(true); onReady?.(num) }}
        onError={() => setLoaded(false)} />
    </div>
  )
}
