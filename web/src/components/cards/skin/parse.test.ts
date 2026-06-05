import { describe, it, expect } from 'vitest'
import { parseEmphasis, parseCompareRows, rowsToRaw, type CompareRow } from './parse'

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
