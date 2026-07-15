import { describe, it, expect } from 'vitest'
import { extractEidText } from './deckDiff'

describe('extractEidText', () => {
  it('data-eid 요소의 텍스트를 태그 제거해 추출', () => {
    const html = '<div data-screen-label="01"><h1 data-eid="e1">제목 <b>강조</b></h1></div>'
    expect(extractEidText(html, 'e1')).toBe('제목 강조')
  })

  it('중첩된 동일 태그를 depth로 올바르게 닫음', () => {
    const html = '<div data-eid="ex">겉 <div>안</div> 끝</div>'
    expect(extractEidText(html, 'ex')).toBe('겉 안 끝')
  })

  it('없는 eid는 null', () => {
    expect(extractEidText('<p data-eid="a">x</p>', 'nope')).toBeNull()
  })

  it('void 요소(img)는 빈 문자열', () => {
    expect(extractEidText('<img data-eid="im" src="x">', 'im')).toBe('')
  })

  it('정규식 특수문자가 든 eid도 안전', () => {
    expect(extractEidText('<p data-eid="a.b">x</p>', 'a.b')).toBe('x')
  })
})
