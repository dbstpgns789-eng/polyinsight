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
