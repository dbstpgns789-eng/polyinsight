// 이미지 초점(focal point) 순수 유틸. {x,y}는 0~1 정규화 좌표.

export interface Focal {
  x: number
  y: number
}

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n))
}

export function clampFocal(f: Focal): Focal {
  return { x: clamp01(f.x), y: clamp01(f.y) }
}

interface Rect {
  left: number
  top: number
  width: number
  height: number
}

/** 클릭 좌표(clientX/Y)를 요소 rect 기준 0~1 focal로 변환(클램프 포함). */
export function clickToFocal(clientX: number, clientY: number, rect: Rect): Focal {
  return clampFocal({
    x: (clientX - rect.left) / rect.width,
    y: (clientY - rect.top) / rect.height,
  })
}

/** focal → CSS objectPosition 문자열. 없으면 'center'. */
export function focalToObjectPosition(focal?: Focal): string {
  if (!focal) return 'center'
  const { x, y } = clampFocal(focal)
  return `${x * 100}% ${y * 100}%`
}
