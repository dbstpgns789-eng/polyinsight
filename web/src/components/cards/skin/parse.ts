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

const _MYTH_LABELS = new Set(['오해', '통념', '거짓', 'myth', 'fiction'])
const _TRUTH_LABELS = new Set(['진실', '사실', 'truth', 'fact'])

/** mythbuster pairs 오염 복구(렌더러 강건화).
 *  S6가 "오해내용:진실내용"(정상) 대신 "오해:내용|진실:내용|..."처럼 라벨을 접두로 뱉으면
 *  parsePairs는 a="오해"(리터럴 라벨)·b=내용으로 잘못 쪼갠다 → 좌측칸에 "오해" 글자만 박힘.
 *  a가 리터럴 라벨인 항목이 과반이면 오염으로 보고, 오해항목.b/진실항목.b를 한 쌍으로 재조립. */
export function repairFaceoffPairs(pairs: Pair[]): Pair[] {
  const norm = (s: string) => s.trim().toLowerCase()
  const isLabel = (s: string) => _MYTH_LABELS.has(norm(s)) || _TRUTH_LABELS.has(norm(s))
  const polluted = pairs.length > 0 && pairs.filter((p) => isLabel(p.a)).length >= Math.ceil(pairs.length / 2)
  if (!polluted) return pairs

  const out: Pair[] = []
  let pendingMyth: string | null = null
  for (const p of pairs) {
    const label = norm(p.a)
    if (_MYTH_LABELS.has(label)) {
      if (pendingMyth !== null) out.push({ a: pendingMyth, b: '' })
      pendingMyth = p.b
    } else if (_TRUTH_LABELS.has(label)) {
      out.push({ a: pendingMyth ?? '', b: p.b })
      pendingMyth = null
    } else {
      if (pendingMyth !== null) { out.push({ a: pendingMyth, b: '' }); pendingMyth = null }
      out.push(p)
    }
  }
  if (pendingMyth !== null) out.push({ a: pendingMyth, b: '' })
  return out
}

export interface StatItem {
  label: string
  value: string
  unit: string
}

/** 단위 정규화(데이터 클렌징): S6가 "percent"/"percent_point" 영문을 뱉어도 기호로.
 *  카드뉴스 타이포에서 칙칙한 영문 단위를 %·%p 기호로 통일. 매칭 안 되면 원본 유지. */
export function normalizeUnit(unit: string): string {
  const u = unit.trim()
  const key = u.toLowerCase().replace(/[\s_-]/g, '')
  const MAP: Record<string, string> = {
    percent: '%', percentage: '%', pct: '%', 퍼센트: '%',
    percentpoint: '%p', percentagepoint: '%p', pp: '%p', 퍼센트포인트: '%p', 'percentpoints': '%p',
  }
  return MAP[key] ?? u
}

/** "라벨:값:단위|..." → StatItem[] (multistat 뼈대). 라벨 비면 버림. 단위는 정규화. */
export function parseStats(raw: string | undefined): StatItem[] {
  if (!raw) return []
  return raw.split('|').map((seg) => {
    const [label = '', value = '', unit = ''] = seg.split(':')
    return { label: label.trim(), value: value.trim(), unit: normalizeUnit(unit) }
  }).filter((s) => s.label.length > 0)
}

/** StatItem[] → "라벨:값:단위|...". parseStats의 역. */
export function statsToRaw(items: StatItem[]): string {
  return items.map((s) => `${s.label}:${s.value}:${s.unit}`).join('|')
}

export interface TableRow {
  attr: string
  a: string
  b: string
}

/** "속성:A값:B값|..." → TableRow[] (compare_table 뼈대). 속성 비면 버림. */
export function parseTableRows(raw: string | undefined): TableRow[] {
  if (!raw) return []
  return raw.split('|').map((seg) => {
    const [attr = '', a = '', b = ''] = seg.split(':')
    return { attr: attr.trim(), a: a.trim(), b: b.trim() }
  }).filter((r) => r.attr.length > 0)
}

/** TableRow[] → "속성:A:B|...". parseTableRows의 역. */
export function tableRowsToRaw(rows: TableRow[]): string {
  return rows.map((r) => `${r.attr}:${r.a}:${r.b}`).join('|')
}
