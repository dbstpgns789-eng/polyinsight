import { describe, it, expect } from 'vitest'
import { parseEmphasis, parseCompareRows, rowsToRaw, compareBarValue, type CompareRow } from './parse'

describe('compareBarValue', () => {
  it('퍼센트 기호 제거', () => { expect(compareBarValue('20.78%')).toBe(20.78) })
  it('텍스트 섞인 값에서 숫자 추출', () => { expect(compareBarValue('11.1% 감소')).toBe(11.1) })
  it('순수 숫자', () => { expect(compareBarValue('8.44')).toBe(8.44) })
  it('천단위 콤마 제거', () => { expect(compareBarValue('1,234')).toBe(1234) })
  it('비수치는 0', () => { expect(compareBarValue('우수')).toBe(0) })
  it('빈 값은 0', () => { expect(compareBarValue('')).toBe(0) })
})

describe('parseEmphasis', () => {
  it('별표 구간을 em=true로 분리', () => {
    expect(parseEmphasis('기존보다 *더 단단*하다')).toEqual([
      { text: '기존보다 ', em: false },
      { text: '더 단단', em: true },
      { text: '하다', em: false },
    ])
  })
  it('별표 없으면 단일 비강조 세그먼트', () => {
    expect(parseEmphasis('강조 없음')).toEqual([{ text: '강조 없음', em: false }])
  })
  it('빈 문자열은 빈 배열', () => {
    expect(parseEmphasis('')).toEqual([])
  })
})

describe('parseCompareRows', () => {
  it('label:value:primary 행을 파싱', () => {
    expect(parseCompareRows('우리:238:1|PP:199:0')).toEqual([
      { label: '우리', value: '238', primary: true },
      { label: 'PP', value: '199', primary: false },
    ])
  })
  it('빈 입력은 빈 배열', () => {
    expect(parseCompareRows(undefined)).toEqual([])
  })
  it('라벨 없는 행은 버림', () => {
    expect(parseCompareRows('::1|좋음:10:0')).toEqual([
      { label: '좋음', value: '10', primary: false },
    ])
  })
})

describe('rowsToRaw ↔ parseCompareRows 라운드트립', () => {
  it('파싱→재조립이 동일 데이터를 보존', () => {
    const rows: CompareRow[] = [
      { label: '우리 복합 구슬', value: '238', primary: true },
      { label: '무보강 셀룰로스', value: '142', primary: false },
    ]
    expect(parseCompareRows(rowsToRaw(rows))).toEqual(rows)
  })
})

import { parsePairs, pairsToRaw, type Pair } from './parse'

describe('parsePairs / pairsToRaw', () => {
  it('a:b 쌍 목록 파싱', () => {
    expect(parsePairs('온도:±0.4|습도:2%')).toEqual([
      { a: '온도', b: '±0.4' },
      { a: '습도', b: '2%' },
    ])
  })
  it('b 없으면 빈 문자열', () => {
    expect(parsePairs('수집|정제|보정')).toEqual([
      { a: '수집', b: '' }, { a: '정제', b: '' }, { a: '보정', b: '' },
    ])
  })
  it('빈 입력은 빈 배열', () => {
    expect(parsePairs(undefined)).toEqual([])
  })
  it('a 없는 항목은 버림', () => {
    expect(parsePairs(':x|좋음:1')).toEqual([{ a: '좋음', b: '1' }])
  })
  it('라운드트립 보존', () => {
    const ps: Pair[] = [{ a: '제목', b: '본문' }, { a: '단독', b: '' }]
    expect(parsePairs(pairsToRaw(ps))).toEqual(ps)
  })
})
