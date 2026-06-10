import { describe, it, expect } from 'vitest'
import { applyFieldStyle, clampTracking } from './fieldStyle'

describe('clampTracking', () => {
  it('범위 내 값은 그대로', () => { expect(clampTracking(0.02)).toBe(0.02) })
  it('최댓값 초과는 0.1로 클램프', () => { expect(clampTracking(0.5)).toBe(0.1) })
  it('최솟값 미만은 -0.05로 클램프', () => { expect(clampTracking(-1)).toBe(-0.05) })
  it('NaN은 0', () => { expect(clampTracking(NaN)).toBe(0) })
})

describe('applyFieldStyle', () => {
  const base = { fontSize: 'var(--set-headline)', fontWeight: 800, color: 'var(--set-ink-strong)' }

  it('override 없으면 base 그대로', () => {
    expect(applyFieldStyle(base, undefined)).toEqual(base)
  })
  it('size는 역할 토큰에 배수 calc 적용', () => {
    expect(applyFieldStyle(base, { size: 'L' }).fontSize).toBe('calc((var(--set-headline)) * 1.18)')
  })
  it('color는 set 토큰으로 치환', () => {
    expect(applyFieldStyle(base, { color: 'accent' }).color).toBe('var(--set-accent)')
  })
  it('weight bold는 700', () => {
    expect(applyFieldStyle(base, { weight: 'bold' }).fontWeight).toBe(700)
  })
  it('align은 textAlign으로', () => {
    expect(applyFieldStyle(base, { align: 'center' }).textAlign).toBe('center')
  })
  it('tracking은 em + 클램프', () => {
    expect(applyFieldStyle(base, { tracking: 0.9 }).letterSpacing).toBe('0.1em')
  })
  it('base를 변형하지 않음(불변)', () => {
    applyFieldStyle(base, { color: 'accent' })
    expect(base.color).toBe('var(--set-ink-strong)')
  })
})
