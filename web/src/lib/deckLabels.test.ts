import { describe, it, expect } from 'vitest'
import { extractCardLabels } from './deckLabels'

// 실 저작 덱 구조 미러: 마스트헤드 "KITECH NN / 07" + kicker "영문ROLE · 한글부제" + 헤드라인.
const card = (n: string, inner: string, attrs = '') =>
  `<div data-screen-label="${n}"${attrs} style="width:1080px;height:1350px">${inner}</div>`

describe('extractCardLabels', () => {
  it('빈/누락 HTML → []', () => {
    expect(extractCardLabels(null)).toEqual([])
    expect(extractCardLabels(undefined)).toEqual([])
    expect(extractCardLabels('')).toEqual([])
  })

  it('1순위: data-role 명시 역할을 그대로 쓴다', () => {
    const html =
      card('01', '<h1>표지</h1>', ' data-role="표지"') +
      card('02', '<span>WHY</span> · <span>왜 이게 문제였나</span>', ' data-role="문제"')
    expect(extractCardLabels(html)).toEqual(['표지', '문제'])
  })

  it('첫 장은 data-role 없으면 표지(마스트헤드 middot 오매치 전에)', () => {
    // 커버 마스트헤드 "KITECH · 한국생산기술연구원 CELLULOSE · 2024"
    const html = card('01', 'KITECH · 한국생산기술연구원 CELLULOSE · 2024 MICROBEAD · 미세플라스틱')
    expect(extractCardLabels(html)).toEqual(['표지'])
  })

  it('폴백: 영문역할 kicker 뒤 한글 부제를 단어경계로 다듬어 취한다', () => {
    const html =
      card('01', '표지', ' data-role="표지"') +
      // 부제가 길면(cap 초과) 단어경계로 다듬어 헤드라인 "치약…" 번짐 제거
      card('02', 'KITECH 02 / 07 <div>WHY · 왜 이게 문제였나</div> <h2>치약·세안제 속 그 작은 알갱이</h2>')
    expect(extractCardLabels(html)).toEqual(['표지', '왜 이게 문제였나'])
  })

  it('폴백 한계: 짧은 부제엔 헤드라인이 한 단어 번질 수 있다(data-role이 깔끔한 이유)', () => {
    // "부서지는 힘"(짧음) 뒤 헤드라인 "구슬…"이 cap 안에 들어와 한 단어 번짐 — 휴리스틱의 본질적 한계.
    // 깨진 라벨이 아니라 다소 긴 라벨(레일이 CSS truncate). 정본 해법=data-role.
    const html =
      card('01', '표지') +
      card('03', 'KITECH 03 / 07 <div>THE NUMBER · 부서지는 힘</div> <h2>구슬 하나를 눌러 부쉈다</h2>')
    expect(extractCardLabels(html)).toEqual(['표지', '부서지는 힘 구슬'])
  })

  it('회귀: 본문 middot(세안제·치약)이 아니라 최상단 영문 kicker를 잡는다', () => {
    const html =
      card('01', '표지') +
      card('04', 'KITECH 04 / 07 <div>THE CATCH · 그런데 천연 구슬은 너무 물렀다</div> 세안제·치약 속에서')
    // 옛 버그: "세안제". 이제 kicker 부제.
    const out = extractCardLabels(html)
    expect(out[1]).not.toBe('세안제')
    expect(out[1]).toBe('그런데 천연 구슬은')
  })

  it('회귀: 소속 표기(한글·한글)는 라벨로 안 잡고 null(→CARD 0N)', () => {
    const html =
      card('01', '표지') +
      // 마감 카드: 영문역할 kicker 없음, 소속 "한국생산기술연구원 · 융합기술연구소"만
      card('07', 'KITECH 07 / 07 <h1>플라스틱을 대신할 구슬</h1> <p>한국생산기술연구원 · 융합기술연구소</p>')
    // 옛 버그: "술연구원 융합기술연구소"(12자 잘림). 이제 null.
    expect(extractCardLabels(html)).toEqual(['표지', null])
  })

  it('kicker 없는 카드 → null (레일이 CARD 0N 폴백)', () => {
    const html = card('01', '표지') + card('02', '<h1>그냥 헤드라인만 있는 카드</h1>')
    expect(extractCardLabels(html)).toEqual(['표지', null])
  })

  it('data-role이 kicker보다 우선', () => {
    const html =
      card('01', '표지') +
      card('02', 'KITECH 02 / 07 <div>WHY · 왜 이게 문제였나</div>', ' data-role="배경"')
    expect(extractCardLabels(html)).toEqual(['표지', '배경'])
  })
})
