// target 요소(data-eid)의 텍스트를 HTML 문자열에서 추출 — before/after 프리뷰용.
// 백엔드에 HTML 파서가 없고(fidelity=regex only), 브라우저 DOM에도 의존하지 않는다(node 유닛 테스트 가능).
// 최선노력 추출: 여는 태그 탐색 → 동일 태그명 depth 스캔으로 닫는 태그 찾기 → 내부 태그 제거·공백 정규화.

const VOID_TAGS = new Set([
  'img', 'br', 'hr', 'input', 'source', 'area', 'base', 'col', 'embed', 'link', 'meta', 'param', 'track', 'wbr',
])

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function extractEidText(html: string, eid: string): string | null {
  const open = new RegExp(`<([a-zA-Z][\\w-]*)\\b[^>]*\\bdata-eid="${escapeRe(eid)}"[^>]*>`, 'i')
  const m = open.exec(html)
  if (!m) return null
  const tag = m[1].toLowerCase()
  if (VOID_TAGS.has(tag)) return ''
  const bodyStart = m.index + m[0].length

  const scan = new RegExp(`<(/?)${escapeRe(tag)}\\b[^>]*>`, 'gi')
  scan.lastIndex = bodyStart
  let depth = 1
  let end = html.length
  let mm: RegExpExecArray | null
  while ((mm = scan.exec(html)) !== null) {
    if (mm[1] === '/') {
      if (--depth === 0) { end = mm.index; break }
    } else {
      depth++
    }
  }
  return html.slice(bodyStart, end).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}
