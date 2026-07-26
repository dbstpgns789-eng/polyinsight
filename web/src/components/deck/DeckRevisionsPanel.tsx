'use client'

// 판 목록 — 되돌아갈 지점. 자동저장은 여기 안 쌓인다(3초마다 쌓으면 고를 수 없는 목록이 된다).
// 서버 보관이라 새로고침해도 살아있다 — iframe undo·AI 되돌리기는 브라우저 메모리라 함께 죽는다.

import type { DeckRevision } from '@/lib/api'

interface Props {
  items: DeckRevision[]
  busyId?: number | null
  onRestore: (revId: number) => void
}

const SOURCE: Record<DeckRevision['source'], string> = {
  author: 'AI 원본',
  manual: '저장',
  ai_edit: 'AI 편집',
  restore: '되돌림',
}

function ago(iso: string): string {
  const t = Date.parse(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  if (Number.isNaN(t)) return ''
  const m = Math.floor((Date.now() - t) / 60000)
  if (m < 1) return '방금'
  if (m < 60) return `${m}분 전`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}시간 전`
  return `${Math.floor(h / 24)}일 전`
}

export default function DeckRevisionsPanel({ items, busyId, onRestore }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">판 기록</div>
        <span className="font-mono text-[10.5px] text-ink-3 bg-bg-subtle rounded px-1.5 py-0.5 tabular-nums">{items.length}</span>
      </div>

      {items.length === 0 ? (
        <p className="text-[11.5px] text-ink-3 leading-relaxed">아직 되돌아갈 판이 없어요.</p>
      ) : (
        <ul className="flex flex-col gap-0.5 max-h-[280px] overflow-y-auto -mx-1 px-1">
          {items.map((r, i) => (
            <li key={r.id}>
              <div className="w-full flex items-center gap-2.5 px-2 h-9 rounded-lg text-ink-2 hover:bg-bg-subtle transition-colors">
                <span className="flex-1 min-w-0 truncate text-[12px]">
                  {SOURCE[r.source] ?? r.source}
                  <span className="text-ink-3 text-[11px]"> · {ago(r.createdAt)}</span>
                </span>
                {i === 0 ? (
                  <span className="shrink-0 font-mono text-[10px] text-ink-3">현재</span>
                ) : (
                  <button onClick={() => onRestore(r.id)} disabled={busyId != null}
                    className="shrink-0 text-[11px] px-2 h-6 rounded-md border border-border text-ink-2
                               hover:bg-bg-subtle disabled:opacity-40 transition-colors">
                    {busyId === r.id ? '되돌리는 중…' : '되돌리기'}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="text-[10.5px] text-ink-3 leading-relaxed">
        저장·AI 편집처럼 큰 변화만 판으로 남아요. 되돌린 것도 판으로 남아서 다시 앞으로 갈 수 있어요.
      </p>
    </div>
  )
}
