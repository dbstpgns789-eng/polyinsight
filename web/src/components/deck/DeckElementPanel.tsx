'use client'

// 선택된 덱 요소 편집 패널 (Phase 3b + 3e 다중선택).
// 단일: 색·폰트크기·정렬·굵기·삭제·순서 + 수치 X/Y·W/H.
// 다중(2개+): 정렬 6버튼 + 분배(3개+) + 수치 X/Y(집합 이동). W/H는 읽기전용(그룹 스케일=범위 밖).
// 자유 드래그/리사이즈는 캔버스에서 직접(직접조작). 여기선 정밀·일괄 조작.

import { useState } from 'react'
import type { SelectedInfo, AlignAxis } from './DeckEditor'

interface Props {
  selected: SelectedInfo | null
  onStyle: (prop: string, value: string) => void
  onDelete: () => void
  onMove: (dir: 'up' | 'down') => void
  onRevertFlow: () => void
  onAlign: (axis: AlignAxis) => void
  onDistribute: (axis: 'h' | 'v') => void
  onSetRect: (r: { left?: number; top?: number; width?: number; height?: number }) => void
}

function rgbToHex(c: string): string {
  const m = /rgba?\(([^)]+)\)/.exec(c)
  if (!m) return /^#/.test(c) ? c : '#000000'
  const [r, g, b] = m[1].split(',').map((x) => parseInt(x.trim(), 10))
  const h = (n: number) => n.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

// 로컬 상태 + Enter/blur 커밋 수치 필드(키 입력마다 postMessage 금지 → 잰크 방지).
// 포커스가 없을 때만 외부 value로 동기화(선택/조작 변경 반영).
function NumberField({
  label, value, disabled, onCommit,
}: { label: string; value: number | null; disabled?: boolean; onCommit: (v: number) => void }) {
  const [focused, setFocused] = useState(false)
  const [local, setLocal] = useState(value == null ? '' : String(Math.round(value)))
  // 렌더 중 prop 변화 반영(React 권장: effect 없이). 포커스 중엔 사용자 입력 보존.
  const [prev, setPrev] = useState(value)
  if (!focused && value !== prev) {
    setPrev(value)
    setLocal(value == null ? '' : String(Math.round(value)))
  }
  const commit = () => {
    const n = parseFloat(local)
    if (!Number.isNaN(n)) onCommit(n)
  }
  return (
    <label className="flex items-center gap-1.5 text-[11px] text-ink-3">
      <span className="w-4">{label}</span>
      <input
        type="number"
        value={local}
        disabled={disabled}
        onChange={(e) => setLocal(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => { setFocused(false); commit() }}
        onKeyDown={(e) => { if (e.key === 'Enter') { commit(); (e.target as HTMLInputElement).blur() } }}
        className="w-full h-7 px-2 rounded border border-border text-[12px] text-ink-2 tabular-nums disabled:opacity-40 disabled:bg-canvas-subtle"
      />
    </label>
  )
}

const ALIGNS: { axis: AlignAxis; glyph: string; title: string }[] = [
  { axis: 'left', glyph: '⇤', title: '왼쪽 정렬' },
  { axis: 'hcenter', glyph: '⇔', title: '가로 가운데' },
  { axis: 'right', glyph: '⇥', title: '오른쪽 정렬' },
  { axis: 'top', glyph: '⤒', title: '위 정렬' },
  { axis: 'vcenter', glyph: '⇳', title: '세로 가운데' },
  { axis: 'bottom', glyph: '⤓', title: '아래 정렬' },
]

export default function DeckElementPanel({
  selected, onStyle, onDelete, onMove, onRevertFlow, onAlign, onDistribute, onSetRect,
}: Props) {
  if (!selected) {
    return (
      <p className="text-[12px] text-ink-3 leading-relaxed">
        카드 위 요소를 클릭해 선택하세요. Shift+클릭이나 빈 곳 드래그(마퀴)로 여러 개를 함께 선택해
        정렬·분배·이동할 수 있습니다. 텍스트는 바로 수정할 수 있습니다.
      </p>
    )
  }

  const count = selected.count ?? 1
  const multi = count > 1
  const rect = selected.rect ?? null

  const fontPx = parseFloat(selected.styles.fontSize) || 16
  const isBold = (parseInt(selected.styles.fontWeight, 10) || 400) >= 600
  const align = selected.styles.textAlign

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-semibold text-ink-2">
          선택: <code className="text-forest-green">{selected.tag}</code>
        </span>
        {!multi && selected.editable && <span className="text-[10px] text-ink-3">텍스트 직접수정 가능</span>}
      </div>

      {/* 위치: 정렬·분배(다중) + 수치 X/Y·W/H */}
      {(multi || rect) && (
        <div className="flex flex-col gap-2">
          {multi && (
            <>
              <div className="text-[11px] text-ink-3">정렬</div>
              <div className="grid grid-cols-6 gap-1">
                {ALIGNS.map((a) => (
                  <button key={a.axis} title={a.title} onClick={() => onAlign(a.axis)}
                    className="h-7 rounded border border-border text-ink-2 text-[13px] hover:border-forest-green hover:text-forest-green">
                    {a.glyph}
                  </button>
                ))}
              </div>
              <div className="flex gap-1">
                <button onClick={() => onDistribute('h')} disabled={!selected.canDistribute}
                  className="flex-1 h-7 rounded border border-border text-[11px] text-ink-2 disabled:opacity-30 hover:border-forest-green hover:text-forest-green">
                  가로 균등분배
                </button>
                <button onClick={() => onDistribute('v')} disabled={!selected.canDistribute}
                  className="flex-1 h-7 rounded border border-border text-[11px] text-ink-2 disabled:opacity-30 hover:border-forest-green hover:text-forest-green">
                  세로 균등분배
                </button>
              </div>
            </>
          )}

          {rect && (
            <div className="grid grid-cols-2 gap-x-3 gap-y-2">
              <NumberField label="X" value={rect.x} onCommit={(v) => onSetRect({ left: v })} />
              <NumberField label="Y" value={rect.y} onCommit={(v) => onSetRect({ top: v })} />
              <NumberField label="W" value={multi ? null : rect.w} disabled={multi}
                onCommit={(v) => onSetRect({ width: v })} />
              <NumberField label="H" value={multi ? null : rect.h} disabled={multi}
                onCommit={(v) => onSetRect({ height: v })} />
            </div>
          )}
          {multi && (
            <p className="text-[10px] text-ink-3">
              W·H는 여러 요소 크기가 {selected.mixed ? '혼합' : '집합'}이라 읽기 전용입니다.
            </p>
          )}
        </div>
      )}

      {/* 스타일·순서·삭제는 단일 선택에서만 */}
      {!multi && (
        <>
          <div className="h-px bg-border my-1" />

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
        </>
      )}
    </div>
  )
}
