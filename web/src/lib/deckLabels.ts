// 저작 덱 HTML에서 카드별 역할 라벨(kicker의 한글부)을 best-effort 추출.
// 헌법 §1: 형태는 자유 발명이라 라벨이 항상 있진 않음 → 없으면 null(레일이 'CARD 0N'로 폴백).
// kicker 형태 "역할 · 부제"(예: "문제 · THE PROBLEM", "핵심 원리 · pH 반응 메커니즘").
// 부제가 영문 대문자든 한글이든 상관없이, 카드 최상단의 첫 "한글역할 · X"를 취한다.

const MIDDOT = '[\\u00B7\\u2027\\u30FB]'
const KICKER = new RegExp(`([가-힣][가-힣0-9\\s]{0,11}?)\\s*${MIDDOT}\\s*\\S`)

export function extractCardLabels(html: string | null | undefined): (string | null)[] {
  if (!html) return []
  const blocks = html.split(/(?=data-screen-label)/).slice(1)
  return blocks.map((block, i) => {
    const text = block.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
    const label = text.match(KICKER)?.[1]?.trim()
    if (label && label.length >= 2 && label.length <= 12) return label
    return i === 0 ? '표지' : null   // 첫 장은 표지 관례로 폴백
  })
}
