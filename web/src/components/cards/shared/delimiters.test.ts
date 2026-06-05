import { describe, it, expect } from 'vitest'
import { parseColon, joinColon, parsePipe, joinPipe, parseDot, joinDot } from './delimiters'

describe('colon round-trip (주석: 내부 콜론 strip)', () => {
  it('label:sub 분리/조합', () => {
    expect(parseColon('라벨:서브')).toEqual({ label: '라벨', sub: '서브' })
    expect(joinColon('라벨', '서브')).toBe('라벨:서브')
  })
  it('내부 콜론은 strip되어 round-trip 안전', () => {
    expect(joinColon('a:b', 'c:d')).toBe('ab:cd')
  })
  it('sub 없으면 label만', () => {
    expect(joinColon('라벨', '')).toBe('라벨')
  })
})

describe('pipe', () => {
  it('split/join + 내부 파이프 strip', () => {
    expect(parsePipe('a|b|c')).toEqual(['a', 'b', 'c'])
    expect(joinPipe(['a|x', 'b'])).toBe('ax|b')
  })
})

describe('dot', () => {
  it('· 구분 split/join', () => {
    expect(parseDot('a · b · c')).toEqual(['a', 'b', 'c'])
    expect(joinDot(['a', 'b'])).toBe('a · b')
  })
})
