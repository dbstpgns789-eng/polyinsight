'use client'

// 선택된 덱 요소 재스타일 패널 (Phase 3b) — 색·폰트크기·정렬·굵기·삭제·순서.
// 자유 드래그/리사이즈는 보류(객체모델 = v3.0 재감금). 여기선 국소 재스타일만.

import type { SelectedInfo } from './DeckEditor'

interface Props {
  selected: SelectedInfo | null
  onStyle: (prop: string, value: string) => void
  onDelete: () => void
  onMove: (dir: 'up' | 'down') => void
  onRevertFlow: () => void
}

function rgbToHex(c: string): string {
  const m = /rgba?\(([^)]+)\)/.exec(c)
  if (!m) return /^#/.test(c) ? c : '#000000'
  const [r, g, b] = m[1].split(',').map((x) => parseInt(x.trim(), 10))
  const h = (n: number) => n.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

export default function DeckElementPanel({ selected, onStyle, onDelete, onMove, onRevertFlow }: Props) {
  if (!selected) {
    return (
      <p className="text-[12px] text-ink-3 leading-relaxed">
        카드 위 요소를 클릭해 선택하세요. 텍스트는 바로 수정할 수 있고,
        선택한 요소의 색·크기·정렬을 여기서 바꾸거나 삭제·순서변경 할 수 있습니다.
      </p>
    )
  }

  const fontPx = parseFloat(selected.styles.fontSize) || 16
  const isBold = (parseInt(selected.styles.fontWeight, 10) || 400) >= 600
  const align = selected.styles.textAlign

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-semibold text-ink-2">
          선택: <code className="text-forest-green">{selected.tag}</code>
        </span>
        {selected.editable && <span className="text-[10px] text-ink-3">텍스트 직접수정 가능</span>}
      </div>

      <label className="flex items-center justify-between text-[12px] text-ink-2">
        글자색
        <input type="color" defaultValue={rgbToHex(selected.styles.color)}
          onChange={(e) => onStyle('color', e.target.value)}
          className="w-9 h-7 rounded border border-border" />
      </label>

      <label className="flex items-center justify-between text-[12px] text-ink-2">
        배경색
        <input type="color"
          defaultValue={selected.styles.background ? rgbToHex(selected.styles.background) : '#ffffff'}
          onChange={(e) => onStyle('background', e.target.value)}
          className="w-9 h-7 rounded border border-border" />
      </label>

      <div className="flex items-center justify-between text-[12px] text-ink-2">
        글자크기
        <div className="flex items-center gap-1">
          <button onClick={() => onStyle('fontSize', `${Math.max(8, fontPx - 2)}px`)}
            className="w-7 h-7 rounded border border-border text-ink-2">−</button>
          <span className="w-10 text-center tabular-nums">{Math.round(fontPx)}</span>
          <button onClick={() => onStyle('fontSize', `${fontPx + 2}px`)}
            className="w-7 h-7 rounded border border-border text-ink-2">+</button>
        </div>
      </div>

      <div className="flex items-center justify-between text-[12px] text-ink-2">
        정렬
        <div className="flex gap-1">
          {(['left', 'center', 'right'] as const).map((a) => (
            <button key={a} onClick={() => onStyle('textAlign', a)}
              className={`w-7 h-7 rounded border text-[11px] ${align === a ? 'border-forest-green text-forest-green' : 'border-border text-ink-3'}`}>
              {a === 'left' ? '⇤' : a === 'center' ? '↔' : '⇥'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between text-[12px] text-ink-2">
        굵기
        <button onClick={() => onStyle('fontWeight', isBold ? '400' : '700')}
          className={`px-3 h-7 rounded border text-[12px] font-bold ${isBold ? 'border-forest-green text-forest-green' : 'border-border text-ink-3'}`}>
          B
        </button>
      </div>

      <div className="h-px bg-border my-1" />

      <div className="flex gap-2">
        <button onClick={() => onMove('up')}
          className="flex-1 h-8 rounded-lg border border-border text-[12px] text-ink-2">↑ 위로</button>
        <button onClick={() => onMove('down')}
          className="flex-1 h-8 rounded-lg border border-border text-[12px] text-ink-2">아래로 ↓</button>
      </div>

      {selected.absolute && (
        <button onClick={onRevertFlow}
          className="h-8 rounded-lg border border-forest-green text-[12px] text-forest-green">
          ↺ 흐름으로 복귀 (자유배치 해제)
        </button>
      )}

      <button onClick={onDelete}
        className="h-8 rounded-lg border border-red-300 text-[12px] text-red-600">요소 삭제</button>
    </div>
  )
}
