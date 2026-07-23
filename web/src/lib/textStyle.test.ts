import { describe, it, expect } from 'vitest'
import { parseLetterSpacingPx, parseLineHeightRatio, nearestWeightStep, hasTextShadow } from './textStyle'

describe('parseLetterSpacingPx', () => {
  it('normal → 0', () => expect(parseLetterSpacingPx('normal')).toBe(0))
  it('빈값/undefined → 0', () => {
    expect(parseLetterSpacingPx('')).toBe(0)
    expect(parseLetterSpacingPx(undefined)).toBe(0)
  })
  it('px 파싱', () => expect(parseLetterSpacingPx('2px')).toBe(2))
  it('음수 px', () => expect(parseLetterSpacingPx('-0.5px')).toBe(-0.5))
})

describe('parseLineHeightRatio', () => {
  it('computed px를 fontSize로 나눠 배수화 + 1자리 반올림', () =>
    expect(parseLineHeightRatio('24px', '16px')).toBe(1.5))
  it('normal → 1.4 기본', () => expect(parseLineHeightRatio('normal', '16px')).toBe(1.4))
  it('단위없는 배수는 그대로', () => expect(parseLineHeightRatio('1.6', '16px')).toBe(1.6))
  it('fontSize 0/결측 → 1.4', () => {
    expect(parseLineHeightRatio('24px', '0px')).toBe(1.4)
    expect(parseLineHeightRatio('24px', undefined)).toBe(1.4)
  })
})

describe('nearestWeightStep', () => {
  const S = [400, 600, 700, 800]
  it('정확 일치', () => expect(nearestWeightStep('700', S)).toBe(700))
  it('가까운 스텝으로 스냅', () => {
    expect(nearestWeightStep('680', S)).toBe(700)
    expect(nearestWeightStep('430', S)).toBe(400)
  })
  it('결측 → 400 기준', () => expect(nearestWeightStep(undefined, S)).toBe(400))
})

describe('hasTextShadow', () => {
  it('none/빈값 → false', () => {
    expect(hasTextShadow('none')).toBe(false)
    expect(hasTextShadow('')).toBe(false)
    expect(hasTextShadow(undefined)).toBe(false)
  })
  it('실제 그림자 → true', () => expect(hasTextShadow('rgba(0,0,0,0.4) 0px 2px 6px')).toBe(true))
})
