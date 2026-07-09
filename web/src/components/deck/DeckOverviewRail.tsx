'use client'

// 뷰 모드 우측 '덱 개요' 레일 (V2 개요 워크스페이스) — 편집 모드의 도구 레일과 구조 대칭.
// 스토리보드(카드 네비게이터)로 서사 아크를 표면화 + 공백을 목적으로 채운다. 클릭=카드 점프.
import { CardImg } from './DeckViewer'

interface Props {
  jobId: string
  cardCount: number
  ver: number
  index: number                       // 현재 카드(0-based)
  onSelect: (i: number) => void
  title: string                       // 덱/논문 제목
  labels: (string | null)[]           // 카드별 역할 라벨(없으면 null)
}

// 좌측 네비 레일(3패널: 좌 네비 + 중앙 카드 + 우 팩트). 스토리보드로 서사 아크 표면화.
// 접기/펼치기는 경계의 라운드 범프 핸들(page.tsx)이 담당.
export default function DeckOverviewRail({
  jobId, cardCount, ver, index, onSelect, title, labels,
}: Props) {
  const n = Math.max(cardCount, 1)

  return (
    <aside className="w-[300px] shrink-0 border-r border-deck-line bg-surface min-h-0 flex flex-col">
      {/* 헤더 */}
      <div className="px-5 pt-5 pb-4 border-b border-deck-line-soft shrink-0">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-3">덱 개요 · Deck</div>
        <h2 className="mt-2 text-[15px] font-bold text-ink leading-snug line-clamp-2">{title}</h2>
        <div className="mt-1.5 text-[11.5px] text-ink-3">AI 저작 · {n}장 · 1080×1350</div>
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
