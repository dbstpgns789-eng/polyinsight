'use client'

// 레이어 패널 — 카드의 원자 요소 목록(Mirra 파리티). 목록에서 고르면 = 캔버스 클릭 '가림' 우회
// (배경 SVG·풀블리드 이미지처럼 뒤에 깔려 클릭이 안 닿던 요소도 여기선 선택된다). 캔버스 선택과
// 양방향 동기(선택 요소 = 하이라이트). 고른 뒤 이동/리사이즈는 캔버스에서 직접 — 이 패널은 '발견·선택'.

import type { LayerItem, LayerKind } from './DeckEditor'

interface Props {
  items: LayerItem[]
  selectedEid?: string
  onSelect: (eid: string) => void
  onHover?: (eid: string | null) => void   // 행 hover → 캔버스 로케이트(아웃라인)
}

const KIND: Record<LayerKind, { glyph: string; name: string }> = {
  text: { glyph: 'T', name: '글자' },
  image: { glyph: '▣', name: '이미지' },
  graphic: { glyph: '◈', name: '그래픽' },
  shape: { glyph: '▢', name: '도형' },
}

export default function DeckLayersPanel({ items, selectedEid, onSelect, onHover }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">요소 목록</div>
        <span className="font-mono text-[10.5px] text-ink-3 bg-bg-subtle rounded px-1.5 py-0.5 tabular-nums">{items.length}</span>
      </div>

      {items.length === 0 ? (
        <p className="text-[11.5px] text-ink-3 leading-relaxed">이 카드의 요소를 불러오는 중…</p>
      ) : (
        <ul className="flex flex-col gap-0.5 max-h-[280px] overflow-y-auto -mx-1 px-1">
          {items.map((it) => {
            const on = !!selectedEid && it.eid === selectedEid
            const k = KIND[it.kind]
            return (
              <li key={it.eid}>
                <button onClick={() => onSelect(it.eid)} title={it.label || k.name}
                  onMouseEnter={() => onHover?.(it.eid)} onMouseLeave={() => onHover?.(null)}
                  className={`w-full flex items-center gap-2.5 px-2 h-8 rounded-lg text-left transition-colors ${
                    on ? 'bg-forest-green-wash text-forest-green-deep' : 'text-ink-2 hover:bg-bg-subtle'}`}>
                  <span aria-hidden="true"
                    className={`w-5 h-5 shrink-0 grid place-items-center rounded text-[11px] font-mono ${
                      on ? 'text-forest-green-deep' : 'text-ink-3'}`}>{k.glyph}</span>
                  <span className="flex-1 min-w-0 truncate text-[12px]">{it.label || k.name}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <p className="text-[10.5px] text-ink-3 leading-relaxed">
        목록에서 고르면 뒤에 가려진 그래픽·이미지도 선택돼요. 고른 뒤 캔버스에서 끌어 옮기거나 크기를 바꿀 수 있어요.
      </p>
    </div>
  )
}
