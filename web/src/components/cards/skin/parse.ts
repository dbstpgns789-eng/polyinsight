// 카드 피부의 순수 파싱 로직. React 의존 없음 → 단위테스트 대상.
// Headline(강조)·CompareBars(비교행)·BigStatCompare 뼈대가 여기서 import.

/** "a *b* c" → [{text:'a ',em:false},{text:'b',em:true},{text:' c',em:false}] */
export function parseEmphasis(value: string): Array<{ text: string; em: boolean }> {
  const out: Array<{ text: string; em: boolean }> = []
  const re = /\*([^*]+)\*/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(value)) !== null) {
    if (m.index > last) out.push({ text: value.slice(last, m.index), em: false })
    out.push({ text: m[1], em: true })
    last = m.index + m[0].length
  }
  if (last < value.length) out.push({ text: value.slice(last), em: false })
  return out
}

export interface CompareRow {
  label: string
  value: string      // 숫자 문자열(표시 + 너비 계산)
  primary: boolean
}

/** "a:238:1|b:199:0" → CompareRow[] */
export function parseCompareRows(raw: string | undefined): CompareRow[] {
  if (!raw) return []
  return raw.split('|').map((seg) => {
    const [label = '', value = '', primary = '0'] = seg.split(':')
    return { label: label.trim(), value: value.trim(), primary: primary.trim() === '1' }
  }).filter((r) => r.label.length > 0)
}

/** CompareRow[] → "a:238:1|b:199:0". parseCompareRows의 역. */
export function rowsToRaw(rows: CompareRow[]): string {
  return rows.map((r) => `${r.label}:${r.value}:${r.primary ? '1' : '0'}`).join('|')
}

/** bars 값 문자열에서 막대 너비용 숫자를 안전 추출.
 *  "20.78%"→20.78, "11.1% 감소"→11.1, "1,234"→1234, "우수"·""→0.
 *  (S6가 단위·텍스트를 섞어 출력해도 막대가 망가지지 않도록 — 견고성) */
export function compareBarValue(value: string): number {
  const n = parseFloat((value ?? '').replace(/[^0-9.\-]/g, ''))
  return Number.isFinite(n) ? n : 0
}

export interface Pair {
  a: string
  b: string
}

/** "a:b|a:b" → Pair[] (b 선택). a 비면 버림. */
export function parsePairs(raw: string | undefined): Pair[] {
  if (!raw) return []
  return raw.split('|').map((seg) => {
    const idx = seg.indexOf(':')
    const a = (idx < 0 ? seg : seg.slice(0, idx)).trim()
    const b = (idx < 0 ? '' : seg.slice(idx + 1)).trim()
    return { a, b }
  }).filter((p) => p.a.length > 0)
}

/** Pair[] → "a:b|a:b". parsePairs의 역. */
export function pairsToRaw(pairs: Pair[]): string {
  return pairs.map((p) => (p.b ? `${p.a}:${p.b}` : p.a)).join('|')
}
