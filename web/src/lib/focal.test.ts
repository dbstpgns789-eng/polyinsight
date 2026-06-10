import { describe, it, expect } from 'vitest'
import { clampFocal, clickToFocal, focalToObjectPosition } from './focal'

describe('clampFocal', () => {
  it('0~1 범위로 클램프', () => {
    expect(clampFocal({ x: -0.5, y: 1.7 })).toEqual({ x: 0, y: 1 })
  })
  it('범위 안 값은 보존', () => {
    expect(clampFocal({ x: 0.3, y: 0.8 })).toEqual({ x: 0.3, y: 0.8 })
  })
})

describe('clickToFocal', () => {
  it('클릭 좌표를 rect 기준 비율로 변환', () => {
    const rect = { left: 100, top: 200, width: 400, height: 400 }
    expect(clickToFocal(300, 400, rect)).toEqual({ x: 0.5, y: 0.5 })
  })
  it('rect 밖 클릭은 클램프', () => {
    const rect = { left: 0, top: 0, width: 200, height: 200 }
    expect(clickToFocal(-50, 250, rect)).toEqual({ x: 0, y: 1 })
  })
})

describe('focalToObjectPosition', () => {
  it('undefined면 center', () => {
    expect(focalToObjectPosition(undefined)).toBe('center')
  })
  it('focal을 퍼센트 문자열로', () => {
    expect(focalToObjectPosition({ x: 0.25, y: 0.75 })).toBe('25% 75%')
  })
})
