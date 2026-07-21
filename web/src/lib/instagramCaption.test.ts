import { describe, expect, it } from 'vitest'
import { buildInstagramCaption } from './instagramCaption'

describe('buildInstagramCaption — 캡션 본문 + 해시태그를 클립보드용으로 합친다', () => {
  it('본문과 해시태그를 두 줄 띄워 합친다', () => {
    expect(buildInstagramCaption('천연 셀룰로오스가 플라스틱보다 단단해졌다.', ['연구', '셀룰로오스']))
      .toBe('천연 셀룰로오스가 플라스틱보다 단단해졌다.\n\n#연구 #셀룰로오스')
  })

  it('# 없는 해시태그에 #를 붙인다', () => {
    expect(buildInstagramCaption('본문', ['연구'])).toBe('본문\n\n#연구')
  })

  it('이미 #가 있는 해시태그는 중복으로 붙이지 않는다', () => {
    expect(buildInstagramCaption('본문', ['#연구'])).toBe('본문\n\n#연구')
  })

  it('해시태그가 없으면 본문만 반환한다 (뒤 개행 없음)', () => {
    expect(buildInstagramCaption('본문만', [])).toBe('본문만')
  })

  it('해시태그 내부 공백은 제거한다 (인스타 태그는 공백 불가)', () => {
    expect(buildInstagramCaption('x', ['나노 시트'])).toBe('x\n\n#나노시트')
  })

  it('빈 문자열/공백뿐인 해시태그는 버린다', () => {
    expect(buildInstagramCaption('x', ['연구', '', '  '])).toBe('x\n\n#연구')
  })
})
