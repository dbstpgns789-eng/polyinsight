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
    <div className="relative flex flex-col items-center justify-center gap-5 h-full overflow-y-auto px-6 py-8">
      {/* 은은한 중립 도트 그리드 — 빈 캔버스를 '의도된 여백'으로 (museum wall) */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(oklch(20% 0 0 / 0.05) 1px, transparent 1px)',
          backgroundSize: '26px 26px',
          maskImage: 'radial-gradient(ellipse 68% 66% at 50% 46%, #000 42%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(ellipse 68% 66% at 50% 46%, #000 42%, transparent 100%)',
        }} />
      <div className="absolute top-4 left-6 font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-3 select-none">Viewer · Deck</div>

      <div className="relative z-[1] flex items-center gap-5">
        {n > 1 && (
          <button onClick={() => setIdx((i) => clamp(i - 1))} disabled={idx <= 0} aria-label="이전 카드"
            className="w-9 h-9 rounded-full bg-surface border border-deck-line text-ink-2 shadow-card hover:text-ink disabled:opacity-30 shrink-0 transition-colors">‹</button>
        )}
        {/* 흰 베젤 + elevation 그림자 + 헤어라인 = 카드가 다크·밝은·컬러든 항상 분리된 작품으로 */}
        <div className="relative rounded-2xl bg-surface shadow-modal p-1.5 w-[min(46vh,328px)]">
          <div className="relative rounded-[11px] overflow-hidden" style={{ aspectRatio: '1080 / 1350' }}>
            <CardImg jobId={jobId} num={idx + 1} ver={ver} rendering={rendering} tick={tick} onReady={markReady} />
            <div className="pointer-events-none absolute inset-0 rounded-[11px] shadow-[inset_0_0_0_1px_oklch(20%_0_0_/_0.08)]" aria-hidden="true" />
          </div>
          {!(rendering && !ready.has(idx + 1)) && (
            <button onClick={() => onEditCard(idx)}
              className="absolute left-1/2 -translate-x-1/2 bottom-3.5 bg-surface/96 border border-deck-line text-ink text-[12px] font-bold rounded-lg px-3.5 py-1.5 shadow-card hover:text-forest-green-deep transition-colors">
              ✎ 이 카드 편집
            </button>
          )}
        </div>
        {n > 1 && (
          <button onClick={() => setIdx((i) => clamp(i + 1))} disabled={idx >= n - 1} aria-label="다음 카드"
            className="w-9 h-9 rounded-full bg-surface border border-deck-line text-ink-2 shadow-card hover:text-ink disabled:opacity-30 shrink-0 transition-colors">›</button>
        )}
      </div>

      <div className="relative z-[1] flex flex-col items-center gap-3.5">
        <span className="font-mono text-[12px] tabular-nums text-ink-3"><b className="text-ink font-bold">{String(idx + 1).padStart(2, '0')}</b> / {String(n).padStart(2, '0')}</span>

        {rendering && ready.size < n && (
          <div className="flex items-center gap-2 text-[12px] text-ink-3">
            <span className="w-3.5 h-3.5 rounded-full border-2 border-forest-green border-t-transparent animate-spin" aria-hidden="true" />
            카드 그리는 중 {ready.size} / {n}
          </div>
        )}

        {n > 1 && (
          <div className="flex gap-2 justify-center">
            {Array.from({ length: n }, (_, i) => (
              <button key={i} onClick={() => setIdx(i)} aria-label={`카드 ${i + 1}`}
                className={`w-11 rounded-lg overflow-hidden bg-surface shadow-card transition-[outline] ${i === idx ? 'outline outline-2 outline-ink outline-offset-1' : 'outline outline-1 outline-deck-line'}`}
                style={{ aspectRatio: '1080 / 1350' }}>
                <CardImg jobId={jobId} num={i + 1} ver={ver} thumb rendering={rendering} tick={tick} onReady={markReady} />
              </button>
            ))}
          </div>
        )}
      </div>
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
