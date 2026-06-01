// SlotOverlay — 카드 위에 떠 있는 이미지 슬롯 오버레이.
//
// 사용처: edit 모드 카드의 빈 이미지 슬롯 자리에 위치 마커 표시.
// 슬롯이 채워진 경우(EditableImage가 카드 안에서 직접 렌더링)에는 사용하지 않음.
// 이 컴포넌트는 카드 컴포넌트 외부에서 absolute 좌표로 슬롯 자리를 가리킴 (썸네일 미리보기 등에서 활용).
//
// MidCanvas.tsx:186-191 SLOT_OVERLAY 좌표 dict 이식.

'use client'

import { type CSSProperties } from 'react'
import type { SlotType } from '@/lib/imageSlots'

const SLOT_OVERLAY_POS: Record<SlotType, CSSProperties | null> = {
  bg:          { top: 0,    left: 0,      right: 0,    bottom: 0 },
  inset_top:   { top: 0,    left: 0,      right: 0,    bottom: '60%' },
  inset_right: { top: 0,    left: '62%',  right: 0,    bottom: 0 },
  inner:       { top: '55%', left: '5%',  right: '5%', bottom: '12%' },
  none:        null,
}

interface SlotOverlayProps {
  slotType: SlotType
  children?: React.ReactNode
  className?: string
}

export default function SlotOverlay({ slotType, children, className }: SlotOverlayProps) {
  const pos = SLOT_OVERLAY_POS[slotType]
  if (!pos) return null

  return (
    <div
      className={className}
      style={{ position: 'absolute', ...pos, zIndex: 20, pointerEvents: 'auto' }}
    >
      {children}
    </div>
  )
}

export { SLOT_OVERLAY_POS }
