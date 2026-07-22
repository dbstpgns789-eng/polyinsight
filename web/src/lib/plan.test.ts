import { describe, expect, it } from 'vitest'
import { isPlanGateError, planGateKind, trialLabel } from './plan'

describe('플랜 게이트 에러 식별', () => {
  it('402 ERR-PLAN-EXPORT는 export 게이트로 식별된다', () => {
    const err = Object.assign(new Error('내보내기는 업그레이드 후'), {
      status: 402,
      code: 'ERR-PLAN-EXPORT',
    })
    expect(isPlanGateError(err)).toBe(true)
    expect(planGateKind(err)).toBe('export')
  })

  it('402 ERR-PLAN-AUTHOR는 author 게이트로 식별된다', () => {
    const err = Object.assign(new Error('무료 체험 1덱을 모두'), {
      status: 402,
      code: 'ERR-PLAN-AUTHOR',
    })
    expect(planGateKind(err)).toBe('author')
  })

  it('★429 브루트포스는 플랜 게이트가 아니다 — 페이월 띄우면 안 됨', () => {
    const err = Object.assign(new Error('너무 많은 시도입니다'), {
      status: 429,
      code: 'ERR-AUTH-429',
    })
    expect(isPlanGateError(err)).toBe(false)
    expect(planGateKind(err)).toBe(null)
  })

  it('status가 없는 평범한 에러도 안전하게 처리한다', () => {
    expect(isPlanGateError(new Error('네트워크 오류'))).toBe(false)
    expect(planGateKind(new Error('네트워크 오류'))).toBe(null)
  })

  it('null/undefined가 들어와도 터지지 않는다', () => {
    expect(planGateKind(null)).toBe(null)
    expect(planGateKind(undefined)).toBe(null)
  })

  it('402지만 모르는 code면 플랜 게이트가 아니다', () => {
    const err = Object.assign(new Error('결제 필요'), { status: 402, code: 'ERR-SOMETHING' })
    expect(planGateKind(err)).toBe(null)
  })
})

describe('무료 체험 라벨', () => {
  it('무료 미사용', () => {
    expect(trialLabel({ plan: 'free', freeDecksUsed: 0, freeDeckLimit: 1 })).toBe('무료 체험 · 0 / 1 덱 사용')
  })

  it('무료 소진', () => {
    expect(trialLabel({ plan: 'free', freeDecksUsed: 1, freeDeckLimit: 1 })).toBe('무료 체험 · 1 / 1 덱 사용')
  })

  it('유료는 무료 미터를 보여주지 않는다', () => {
    expect(trialLabel({ plan: 'pro', freeDecksUsed: 1, freeDeckLimit: 1 })).toBe(null)
  })

  it('lab 플랜도 미터를 감춘다', () => {
    expect(trialLabel({ plan: 'lab', freeDecksUsed: 0, freeDeckLimit: 1 })).toBe(null)
  })
})
