import { describe, expect, it } from 'vitest'
import { failureReason } from './failureReason'

describe('failureReason — 실패 원인별로 다른 안내', () => {
  it('★크레딧 소진: "스캔본 탓"이라고 하면 안 된다', () => {
    // 실전(2026-07-14): 크레딧이 떨어져 실패했는데 화면엔 "스캔본 PDF는 텍스트를 못 읽어요"가
    // 무조건 붙어 있었다. 유저가 자기 PDF를 의심하게 만드는 최악의 오안내.
    const r = failureReason([
      "ERR-AUTHOR: Error code: 400 - {'message': 'Your credit balance is too low to access the Anthropic API.'}",
    ])
    expect(r.kind).toBe('credit')
    expect(r.hint).not.toContain('스캔본')
    expect(r.title).not.toContain('credit balance')   // 영문 원문 노출 금지
    expect(r.title).not.toContain('400')
  })

  it('백엔드가 이미 사람 말로 준 크레딧 메시지도 잡는다', () => {
    const r = failureReason(['지금은 카드뉴스를 만들 수 없습니다 — AI 사용량이 한도에 도달했습니다.'])
    expect(r.kind).toBe('credit')
  })

  it('진짜 스캔본일 때만 스캔본 안내', () => {
    const r = failureReason([
      'ABORT-S1: PDF에서 충분한 텍스트를 추출하지 못했습니다 (12단어). 스캔본이거나 논문이 아닐 수 있습니다.',
    ])
    expect(r.kind).toBe('scan')
    expect(r.hint).toContain('스캔본')
  })

  it('알 수 없는 실패는 일반 안내 — 엉뚱한 탓을 하지 않는다', () => {
    const r = failureReason(['ERR-AUTHOR: 저작 결과에 카드가 없습니다'])
    expect(r.kind).toBe('unknown')
    expect(r.hint).not.toContain('스캔본')
  })

  it('warnings가 없어도 죽지 않는다', () => {
    expect(failureReason(undefined).kind).toBe('unknown')
    expect(failureReason([]).kind).toBe('unknown')
  })

  it('크레딧 안내는 "운영자가 곧 복구" — 유저 탓이 아님을 밝힌다', () => {
    const r = failureReason(['credit balance is too low'])
    expect(r.hint).toMatch(/운영자|복구|잠시/)
  })
})
