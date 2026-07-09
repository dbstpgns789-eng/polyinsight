'use client'

// Canva식 컨텍스추얼 플로팅 툴바 — 요소 선택 시 카드 위에 떠서 공통 컨트롤(크기·색·굵기·정렬).
// 도구가 손으로 온다 = 몰입. 상세(위치·삭제 등)는 ⋯ 더보기 → 우측 인스펙터.
import type { SelectedInfo } from './DeckEditor'

function rgbToHex(c: string): string {
  const m = /rgba?\(([^)]+)\)/.exec(c)
  if (!m) return /^#/.test(c) ? c : '#000000'
  const [r, g, b] = m[1].split(',').map((x) => parseInt(x.trim(), 10))
  const h = (n: number) => n.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

interface Props {
  selected: SelectedInfo
  onStyle: (prop: string, value: string) => void
  onOpenInspector: () => void
}

export default function DeckFloatingToolbar({ selected, onStyle, onOpenInspector }: Props) {
  const multi = (selected.count ?? 1) > 1
  const fontPx = parseFloat(selected.styles.fontSize) || 16
  const isBold = (parseInt(selected.styles.fontWeight, 10) || 400) >= 600
  const align = selected.styles.textAlign
  const hex = selected.styles.color ? rgbToHex(selected.styles.color) : '#000000'

  return (
    <div className="flex items-center gap-1 rounded-xl bg-surface border border-deck-line shadow-modal px-1.5 py-1.5 deck-fade-up">
      {multi ? (
        <span className="text-[12px] font-semibold text-ink-2 px-2.5">요소 {selected.count}개 선택됨</span>
      ) : (
        <>
          {/* 크기 */}
          <div className="flex items-center rounded-lg bg-bg-subtle p-0.5">
            <button onClick={() => onStyle('fontSize', `${Math.max(8, fontPx - 2)}px`)} aria-label="글자 작게"
              className="w-6 h-6 grid place-items-center rounded-md text-ink-2 hover:bg-surface transition-colors">−</button>
            <span className="w-8 text-center text-[12px] font-semibold tabular-nums text-ink">{Math.round(fontPx)}</span>
            <button onClick={() => onStyle('fontSize', `${fontPx + 2}px`)} aria-label="글자 크게"
              className="w-6 h-6 grid place-items-center rounded-md text-ink-2 hover:bg-surface transition-colors">+</button>
          </div>
          <span className="w-px h-5 bg-deck-line-soft mx-0.5" aria-hidden="true" />
          {/* 글자색 */}
          <label className="relative w-8 h-8 rounded-lg grid place-items-center hover:bg-bg-subtle cursor-pointer transition-colors" title="글자색">
            <span className="w-5 h-5 rounded-md ring-1 ring-inset ring-deck-line" style={{ background: hex }} aria-hidden="true" />
            <input type="color" defaultValue={hex} onChange={(e) => onStyle('color', e.target.value)}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" aria-label="글자색" />
          </label>
          {/* 굵기 */}
          <button onClick={() => onStyle('fontWeight', isBold ? '400' : '700')} title="굵기"
            className={`w-8 h-8 rounded-lg text-[13px] font-bold transition-colors ${isBold ? 'bg-forest-green-wash text-forest-green-deep' : 'text-ink-2 hover:bg-bg-subtle'}`}>B</button>
          {/* 정렬 */}
          <div className="flex items-center gap-0.5 rounded-lg bg-bg-subtle p-0.5">
            {(['left', 'center', 'right'] as const).map((a) => (
              <button key={a} onClick={() => onStyle('textAlign', a)} title={a}
                className={`w-6 h-6 rounded-md text-[11px] transition-colors ${align === a ? 'bg-surface shadow-card text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>
                {a === 'left' ? '⇤' : a === 'center' ? '↔' : '⇥'}
              </button>
            ))}
          </div>
        </>
      )}
      <span className="w-px h-5 bg-deck-line-soft mx-0.5" aria-hidden="true" />
      <button onClick={onOpenInspector} title="더 많은 편집 (직접 편집)"
        className="w-8 h-8 rounded-lg grid place-items-center text-ink-2 hover:bg-bg-subtle transition-colors">⋯</button>
    </div>
  )
}
