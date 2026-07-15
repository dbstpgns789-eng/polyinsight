import { describe, it, expect } from 'vitest'
import { factBadgeState } from './factBadge'

describe('factBadgeState', () => {
  it('확인필요 0 → 초록 확인 배지', () => {
    expect(factBadgeState({ verified: 36, unverified: 0, claims: [] }, true))
      .toEqual({ tone: 'ok', label: '수치 36 확인', icon: '✓' })
  })
  it('확인필요 ≥1 → 주황 확인필요 배지', () => {
    expect(factBadgeState({ verified: 30, unverified: 2, claims: [] }, true))
      .toEqual({ tone: 'warn', label: '2개 확인 필요', icon: '⚠' })
  })
  it('재검증 불가(canReverify=false) → 중립', () => {
    expect(factBadgeState({ verified: 0, unverified: 0, claims: [] }, false))
      .toEqual({ tone: 'muted', label: '재검증 안 됨', icon: '—' })
  })
  it('verify 없음 → 중립', () => {
    expect(factBadgeState(null, true)).toEqual({ tone: 'muted', label: '검증 없음', icon: '—' })
  })
})
