'use client'

// 편집 우측 탭 셸 (스펙 §4.1). 기본=AI 도우미. 탭은 부모 제어(팩트 배지→팩트 탭 점프).
import type { ReactNode } from 'react'

// 편집 모드 = 편집 도구만(AI 도우미·직접 편집). 팩트체크는 검토 관심사라
// 탭이 아니라 상단 배지→온디맨드 오버레이로 표면화(중복 제거).
export type DeckTab = 'ai' | 'inspector'

interface Props {
  active: DeckTab
  onTab: (t: DeckTab) => void
  ai: ReactNode
  inspector: ReactNode
}

const TABS: { key: DeckTab; label: string }[] = [
  { key: 'ai', label: '✦ AI 도우미' },
  { key: 'inspector', label: '직접 편집' },
]

export default function DeckRightTabs({ active, onTab, ai, inspector }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-1 p-1.5 border-b border-deck-line shrink-0">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => onTab(t.key)}
            className={`flex-1 text-[12px] font-semibold py-1.5 rounded-md ${
              active === t.key ? 'bg-forest-green-wash text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-5">
        <div hidden={active !== 'ai'}>{ai}</div>
        <div hidden={active !== 'inspector'}>{inspector}</div>
      </div>
    </div>
  )
}
