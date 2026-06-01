// Jinja2 템플릿이 사용하는 구분자 파싱/조립 유틸.
// "label:sub" → {label, sub}, "a|b|c" → ['a','b','c']
// CardEditorData 스키마는 그대로 유지되며 분리/조합은 모두 클라이언트 책임.

export interface ColonParts {
  label: string
  sub: string
}

export function parseColon(value: string | undefined): ColonParts {
  if (!value) return { label: '', sub: '' }
  const idx = value.indexOf(':')
  if (idx < 0) return { label: value, sub: '' }
  return { label: value.slice(0, idx), sub: value.slice(idx + 1) }
}

export function joinColon(label: string, sub: string): string {
  // label/sub 내부의 ':'는 round-trip 깨지므로 strip (단위 테스트로 검증)
  const cleanLabel = label.replace(/:/g, '')
  const cleanSub = sub.replace(/:/g, '')
  return cleanSub ? `${cleanLabel}:${cleanSub}` : cleanLabel
}

export function parsePipe(value: string | undefined): string[] {
  if (!value) return []
  return value.split('|').map((s) => s.trim()).filter(Boolean)
}

export function joinPipe(items: string[]): string {
  return items.map((s) => s.replace(/\|/g, '')).join('|')
}

export function parseDot(value: string | undefined): string[] {
  if (!value) return []
  return value.split('·').map((s) => s.trim()).filter(Boolean)
}

export function joinDot(items: string[]): string {
  return items.map((s) => s.replace(/·/g, '')).join(' · ')
}

export type DelimiterStrategy = 'colon' | 'pipe' | 'dot'
