import { describe, expect, it } from 'vitest'
import { isAllClear, suspectClaims, type VerifyData } from './verifyStatus'

const base: VerifyData = { verified: 3, unverified: 0, claims: [] }

describe('verifyStatus', () => {
  it('suspect만 골라낸다 (unresolved는 노이즈라 제외 — 모르면 죄 아님)', () => {
    const derived = [
      { value: '170% 증가', kind: 'pct_change', suspect: true, unresolved: false, verified: false, context: '142→238' },
      { value: '30% 증가', kind: 'pct_change', suspect: false, unresolved: true, verified: false, context: '비교쌍 없음' },
    ]
    const s = suspectClaims({ ...base, derived })
    expect(s).toHaveLength(1)
    expect(s[0].value).toBe('170% 증가')
  })

  it('suspect가 있으면 allClear가 아니다 (초록 완료 문구 억제)', () => {
    const derived = [
      { value: '170% 증가', kind: 'pct_change', suspect: true, unresolved: false, verified: false, context: '' },
    ]
    expect(isAllClear({ ...base, derived })).toBe(false)
  })

  it('unverified 0 + suspect 0 이면 allClear', () => {
    expect(isAllClear({ ...base, derived: [] })).toBe(true)
  })

  it('구 덱(derived 키 없음)도 안전 — 하위호환', () => {
    expect(isAllClear(base)).toBe(true)
    expect(suspectClaims(base)).toEqual([])
  })

  it('verify 자체가 없으면 allClear 아님', () => {
    expect(isAllClear(null)).toBe(false)
    expect(suspectClaims(undefined)).toEqual([])
  })
})

import { reviewQueue } from './verifyStatus'

describe('reviewQueue', () => {
  const verify = {
    verified: 1,
    unverified: 1,
    claims: [
      { value: '49.3 mV', context: 'a', verified: true, card: 0 },
      { value: '999 nm', context: 'b', verified: false, card: 2 },
    ],
    derived: [
      { value: '170% 증가', kind: 'pct_change', suspect: true, unresolved: false, verified: true, context: 'c', card: 1 },
      { value: '2배', kind: 'fold', suspect: false, unresolved: false, verified: true, context: 'd', card: 1 },
    ],
  }

  it('산수 불일치를 먼저, 그 다음 원문 미확인을 담는다', () => {
    const q = reviewQueue(verify)
    expect(q.map((i) => i.value)).toEqual(['170% 증가', '999 nm'])
    expect(q.map((i) => i.card)).toEqual([1, 2])
    expect(q[0].reason).toBe('mismatch')
    expect(q[1].reason).toBe('missing')
  })

  it('검증된 수치와 정합한 파생수치는 담지 않는다', () => {
    expect(reviewQueue(verify).some((i) => i.value === '2배')).toBe(false)
  })

  it('verify가 없으면 빈 큐', () => {
    expect(reviewQueue(null)).toEqual([])
  })
})
