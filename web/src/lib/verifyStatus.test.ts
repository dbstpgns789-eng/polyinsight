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
