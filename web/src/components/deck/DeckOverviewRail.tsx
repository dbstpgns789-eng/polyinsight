'use client'

// 뷰 모드 우측 '덱 개요' 레일 (V2 개요 워크스페이스) — 편집 모드의 도구 레일과 구조 대칭.
// 스토리보드(카드 네비게이터)로 서사 아크를 표면화 + 공백을 목적으로 채운다. 클릭=카드 점프.
import { CardImg } from './DeckViewer'

interface VerifyData { verified: number; unverified: number }

interface Props {
  jobId: string
  cardCount: number
  ver: number
  index: number                       // 현재 카드(0-based)
  onSelect: (i: number) => void
  title: string                       // 덱/논문 제목
  verify: VerifyData | null | undefined
  onOpenFact: () => void
  labels: (string | null)[]           // 카드별 역할 라벨(없으면 null)
}

export default function DeckOverviewRail({
  jobId, cardCount, ver, index, onSelect, title, verify, onOpenFact, labels,
}: Props) {
  const n = Math.max(cardCount, 1)
  const clear = !!verify && verify.unverified === 0

  return (
    <aside className="w-[360px] shrink-0 border-l border-deck-line bg-surface min-h-0 flex flex-col">
      {/* 헤더 */}
      <div className="px-5 pt-5 pb-4 border-b border-deck-line-soft shrink-0">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-3">덱 개요 · Deck</div>
        <h2 className="mt-2 text-[15px] font-bold text-ink leading-snug line-clamp-2">{title}</h2>
        <div className="mt-1.5 text-[11.5px] text-ink-3">AI 저작 · {n}장 · 1080×1350</div>

        {verify && (
          <button onClick={onOpenFact}
            className={`mt-3.5 w-full flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left transition-colors ${
              clear
                ? 'bg-forest-green-wash border-forest-green/25 hover:border-forest-green/50'
                : 'bg-risk-medium-faint border-risk-medium-border hover:brightness-[0.99]'}`}>
            <span className={`w-[18px] h-[18px] rounded-full grid place-items-center text-[10px] text-canvas shrink-0 ${clear ? 'bg-forest-green' : 'bg-risk-medium'}`} aria-hidden="true">{clear ? '✓' : '!'}</span>
            <span className="flex-1 min-w-0">
              <span className={`block text-[12px] font-bold ${clear ? 'text-forest-green-deep' : 'text-risk-medium'}`}>
                {clear ? `${verify.verified}개 수치 · 원문 추적됨` : `${verify.unverified}개 수치 · 확인 필요`}
              </span>
              <span className="block text-[10.5px] text-ink-3">팩트 체크 열기</span>
            </span>
            <span className="text-ink-3 shrink-0" aria-hidden="true">›</span>
          </button>
        )}
      </div>

      {/* 스토리보드 — 카드 네비게이터 */}
      <div className="flex items-baseline justify-between px-5 pt-4 pb-1.5 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">카드 · Storyboard</span>
        <span className="font-mono text-[10.5px] text-ink-3 tabular-nums">{String(index + 1).padStart(2, '0')} / {String(n).padStart(2, '0')}</span>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        <ul className="flex flex-col gap-1">
          {Array.from({ length: n }, (_, i) => {
            const active = i === index
            return (
              <li key={i}>
                <button onClick={() => onSelect(i)} aria-current={active}
                  className={`w-full flex items-center gap-3 rounded-xl p-2 text-left transition-colors ${
                    active ? 'bg-forest-green-wash ring-1 ring-inset ring-forest-green/40' : 'hover:bg-bg-subtle'}`}>
                  <div className={`w-11 rounded-md overflow-hidden bg-surface shadow-card shrink-0 ${active ? 'ring-1 ring-forest-green' : 'ring-1 ring-deck-line'}`}
                    style={{ aspectRatio: '1080 / 1350' }}>
                    <CardImg jobId={jobId} num={i + 1} ver={ver} thumb />
                  </div>
                  <div className="min-w-0">
                    <div className={`font-mono text-[10.5px] tracking-wide ${active ? 'text-forest-green-deep' : 'text-ink-3'}`}>CARD {String(i + 1).padStart(2, '0')}</div>
                    <div className={`text-[13px] font-semibold truncate ${active ? 'text-ink' : 'text-ink-2'}`}>{labels[i] ?? `카드 ${i + 1}`}</div>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </aside>
  )
}
